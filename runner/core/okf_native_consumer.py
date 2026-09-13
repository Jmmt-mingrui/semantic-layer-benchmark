"""Native, file-on-demand consumer for an OKF Markdown bundle.

This module deliberately implements only the operations declared for the OKF
target.  It does not build an embedding index, materialize shared chunks, open
a database, or preload the bundle into an agent context.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
from time import perf_counter
from typing import Any, Iterable, Sequence

import yaml

from runner.core.native_adapter import (
    NativeAdapterError,
    NativeIsolationError,
    NativeRequest,
    NativeResponse,
    assert_declared_operation,
    assert_native_artifact_root,
)


class OkfBundleError(NativeAdapterError):
    """Raised when an OKF bundle is malformed or attempts to escape its root."""


_FRONTMATTER = re.compile(r"\\A---[ \\t]*\\r?\\n(.*?)\\r?\\n---[ \\t]*\\r?\\n", re.DOTALL)
_MARKDOWN_LINK = re.compile(r"(?<!!)\\[[^]]*\\]\\(([^)]+)\\)")
_MAX_SEARCH_RESULTS = 100


@dataclass(frozen=True)
class OkfAccessEvent:
    """Sanitized, in-memory telemetry for one native bundle operation."""

    operation: str
    duration_ms: float
    path: str | None = None
    artifact_sha256: str | None = None
    query_sha256: str | None = None
    result_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OkfNativeConsumer:
    """Consume original OKF files on demand through a closed native surface.

    `bundle_root` must be the declared OKF artifact root.  Every file argument
    is resolved relative to that root and must name a regular, non-symlink
    Markdown file.  Callers must explicitly invoke read/follow/search; this
    class never scans files during construction or preloads their content.
    """

    version = "okf-native-consumer-v0.1"

    def __init__(self, bundle_root: str | Path, target_config: dict[str, Any]) -> None:
        artifact_root = target_config.get("native_surface", {}).get("artifact_root")
        if artifact_root is not None:
            assert_native_artifact_root(str(artifact_root))
        self._target_config = target_config
        self._root = Path(bundle_root)
        if self._root.is_symlink() or not self._root.is_dir():
            raise OkfBundleError("OKF bundle root must be an existing non-symlink directory")
        self._resolved_root = self._root.resolve(strict=True)
        self._events: list[OkfAccessEvent] = []
        self._pending_query_sha256: str | None = None

    def preflight(self, deadline_seconds: float) -> Sequence[NativeResponse]:
        if deadline_seconds <= 0:
            raise OkfBundleError("deadline_seconds must be positive")
        return (
            self._timed("okf.validate_frontmatter", lambda: self.validate_frontmatter()),
            self._timed("okf.validate_links", lambda: self.validate_links()),
        )

    def public_tools(self) -> Sequence[dict[str, Any]]:
        """Return original operation names, without database or shared-search tools."""
        return (
            {"name": "okf.validate_frontmatter", "description": "Validate YAML frontmatter in the OKF bundle."},
            {"name": "okf.validate_links", "description": "Validate local Markdown links in the OKF bundle."},
            {"name": "okf.list_files", "description": "List OKF Markdown files."},
            {"name": "okf.read_file", "description": "Read one original OKF Markdown file."},
            {"name": "okf.follow_link", "description": "Follow one declared local Markdown link."},
            {"name": "okf.search_text", "description": "Literal search over the original OKF Markdown files."},
        )

    def dispatch(self, request: NativeRequest) -> NativeResponse:
        assert_declared_operation(self._target_config, request.operation)
        if request.deadline_seconds <= 0:
            raise OkfBundleError("deadline_seconds must be positive")
        handlers = {
            "okf.validate_frontmatter": self.validate_frontmatter,
            "okf.validate_links": self.validate_links,
            "okf.list_files": lambda: self.list_files(**request.arguments),
            "okf.read_file": lambda: self.read_file(**request.arguments),
            "okf.follow_link": lambda: self.follow_link(**request.arguments),
            "okf.search_text": lambda: self.search_text(**request.arguments),
        }
        handler = handlers.get(request.operation)
        if handler is None:
            raise OkfBundleError(f"Operation is not implemented by the OKF consumer: {request.operation}")
        return self._timed(request.operation, handler)

    def close(self) -> None:
        """No external runtime or database connection is owned by this adapter."""

    def access_events(self) -> tuple[OkfAccessEvent, ...]:
        return tuple(self._events)

    def validate_frontmatter(self) -> dict[str, Any]:
        checked = 0
        without_frontmatter: list[str] = []
        for path in self._markdown_files():
            text = self._read_regular_file(path)
            match = _FRONTMATTER.match(text)
            if match is None:
                without_frontmatter.append(self._relative(path))
                continue
            try:
                frontmatter = yaml.safe_load(match.group(1))
            except yaml.YAMLError as error:
                raise OkfBundleError(f"Invalid YAML frontmatter: {self._relative(path)}") from error
            if not isinstance(frontmatter, dict) or not frontmatter:
                raise OkfBundleError(f"Frontmatter must be a non-empty mapping: {self._relative(path)}")
            checked += 1
        if "index.md" in without_frontmatter:
            raise OkfBundleError("Bundle root index.md must include YAML frontmatter")
        return {
            "status": "ok",
            "checked_files": checked,
            "files_without_frontmatter": without_frontmatter,
        }

    def validate_links(self) -> dict[str, Any]:
        checked = 0
        for source in self._markdown_files():
            text = self._read_regular_file(source)
            for destination in self._local_link_destinations(text):
                self._resolve_path(destination, source.parent)
                checked += 1
        return {"status": "ok", "checked_links": checked}

    def list_files(self, prefix: str = "") -> dict[str, Any]:
        directory = self._resolve_path(prefix, self._root, allow_directory=True) if prefix else self._resolved_root
        files = [path for path in self._markdown_files() if path.is_relative_to(directory)]
        entries = [
            {"path": self._relative(path), "artifact_sha256": self._hash_file(path)}
            for path in files
        ]
        return {"files": entries, "count": len(entries)}

    def read_file(self, path: str) -> dict[str, Any]:
        candidate = self._resolve_path(path, self._root)
        text = self._read_regular_file(candidate)
        return {
            "path": self._relative(candidate),
            "artifact_sha256": self._hash_text(text),
            "content": text,
        }

    def follow_link(self, source_path: str, link: str) -> dict[str, Any]:
        source = self._resolve_path(source_path, self._root)
        source_text = self._read_regular_file(source)
        destinations = set(self._local_link_destinations(source_text))
        normalized_link = self._strip_link_suffix(link)
        if normalized_link not in destinations:
            raise OkfBundleError("follow_link accepts only a local link declared in source_path")
        destination = self._resolve_path(normalized_link, source.parent)
        text = self._read_regular_file(destination)
        return {
            "source_path": self._relative(source),
            "path": self._relative(destination),
            "artifact_sha256": self._hash_text(text),
            "content": text,
        }

    def search_text(self, query: str, limit: int = 20) -> dict[str, Any]:
        if not isinstance(query, str) or not query.strip():
            raise OkfBundleError("search_text query must be a non-empty string")
        if not isinstance(limit, int) or not 1 <= limit <= _MAX_SEARCH_RESULTS:
            raise OkfBundleError(f"search_text limit must be between 1 and {_MAX_SEARCH_RESULTS}")
        needle = query.casefold()
        self._pending_query_sha256 = self._hash_text(query)
        matches: list[dict[str, Any]] = []
        for path in self._markdown_files():
            text = self._read_regular_file(path)
            for line_number, line in enumerate(text.splitlines(), start=1):
                if needle in line.casefold():
                    matches.append(
                        {
                            "path": self._relative(path),
                            "line": line_number,
                            "snippet": line[:500],
                            "artifact_sha256": self._hash_text(text),
                        }
                    )
                    if len(matches) >= limit:
                        return {"matches": matches, "truncated": True}
        return {"matches": matches, "truncated": False}

    def _timed(self, operation: str, handler: Any) -> NativeResponse:
        started = perf_counter()
        output = handler()
        duration_ms = (perf_counter() - started) * 1000
        self._record_event(operation, duration_ms, output)
        return NativeResponse(status="ok", duration_ms=duration_ms, output=output)

    def _record_event(self, operation: str, duration_ms: float, output: dict[str, Any]) -> None:
        path = output.get("path") if isinstance(output.get("path"), str) else None
        artifact_hash = output.get("artifact_sha256") if isinstance(output.get("artifact_sha256"), str) else None
        if artifact_hash is None and isinstance(output.get("files"), list):
            artifact_hash = self._hash_text(json.dumps(output["files"], sort_keys=True, separators=(",", ":")))
        query_hash = None
        if operation == "okf.search_text":
            # Do not retain the caller's raw query in telemetry.
            query_hash, self._pending_query_sha256 = self._pending_query_sha256, None
        result_count = output.get("count")
        if result_count is None:
            result_count = output.get("checked_files")
        if result_count is None:
            result_count = output.get("checked_links")
        if result_count is None and isinstance(output.get("matches"), list):
            result_count = len(output["matches"])
        self._events.append(
            OkfAccessEvent(
                operation=operation,
                duration_ms=round(duration_ms, 3),
                path=path,
                artifact_sha256=artifact_hash,
                query_sha256=query_hash,
                result_count=result_count if isinstance(result_count, int) else None,
            )
        )

    def _markdown_files(self) -> list[Path]:
        files: list[Path] = []
        for candidate in sorted(self._resolved_root.rglob("*.md")):
            if candidate.is_symlink():
                raise OkfBundleError(f"Symlinked bundle files are forbidden: {self._relative(candidate)}")
            if candidate.is_file():
                files.append(candidate)
        return files

    def _resolve_path(self, raw_path: str, base: Path, *, allow_directory: bool = False) -> Path:
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise OkfBundleError("Bundle path must be a non-empty relative string")
        normalized = raw_path.replace("\\", "/")
        pure = PurePosixPath(normalized)
        if pure.is_absolute() or ".." in pure.parts or normalized.startswith("/"):
            raise NativeIsolationError("OKF paths must remain inside the declared bundle root")
        candidate = (base / Path(*pure.parts))
        # Resolve first to prevent traversal through a symlinked parent, then reject
        # symlinks explicitly so a bundle cannot smuggle an external document in.
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as error:
            raise OkfBundleError(f"OKF file does not exist: {raw_path}") from error
        if not resolved.is_relative_to(self._resolved_root):
            raise NativeIsolationError("OKF path resolves outside the declared bundle root")
        probe = candidate
        while probe != self._root.parent:
            if probe.is_symlink():
                raise NativeIsolationError("Symlinks are not allowed in OKF bundle paths")
            if probe == self._root:
                break
            probe = probe.parent
        if allow_directory:
            if not resolved.is_dir():
                raise OkfBundleError(f"OKF directory does not exist: {raw_path}")
        elif not resolved.is_file() or resolved.suffix.lower() != ".md":
            raise OkfBundleError("OKF operations accept only regular Markdown files")
        return resolved

    def _read_regular_file(self, path: Path) -> str:
        if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".md":
            raise OkfBundleError("OKF operations accept only regular Markdown files")
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _strip_link_suffix(link: str) -> str:
        return link.strip().split("#", 1)[0].split("?", 1)[0]

    def _local_link_destinations(self, text: str) -> Iterable[str]:
        for raw_destination in _MARKDOWN_LINK.findall(text):
            destination = raw_destination.strip().strip("<>")
            stripped = self._strip_link_suffix(destination)
            if not stripped or stripped.startswith(("https://", "http://", "mailto:", "#")):
                continue
            yield stripped

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(self._resolved_root).as_posix()

    @staticmethod
    def _hash_text(text: str) -> str:
        return sha256(text.encode("utf-8")).hexdigest()

    def _hash_file(self, path: Path) -> str:
        return self._hash_text(self._read_regular_file(path))
