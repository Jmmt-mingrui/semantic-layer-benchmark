"""A closed, progressive-disclosure host for the benchmark Skill package.

This is a host integration, not a conversion of a Skill into a retrieval corpus.
It exposes metadata at discovery time, reads ``SKILL.md`` only after activation,
and permits individual package references only after activation.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from time import perf_counter
from typing import Any, Sequence

from runner.core.native_adapter import (
    NativeAdapterError,
    NativeIsolationError,
    NativeRequest,
    NativeResponse,
    assert_declared_operation,
)


class SkillHostError(NativeAdapterError):
    """Base error for the native Skill host boundary."""


class SkillPackageError(SkillHostError):
    """Raised when a mounted Skill package is malformed or changes identity."""


class SkillStateError(SkillHostError):
    """Raised when a progressive-disclosure operation is out of order."""


@dataclass(frozen=True)
class SkillIdentity:
    name: str
    description: str
    package_sha256: str
    skill_md_sha256: str
    host_revision: str

    def discovery_metadata(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "package_sha256": self.package_sha256,
            "skill_md_sha256": self.skill_md_sha256,
            "host_revision": self.host_revision,
        }


@dataclass(frozen=True)
class SkillAccessEvent:
    operation: str
    path: str | None
    byte_count: int
    sha256: str | None
    duration_ms: float

    def sanitized(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "path": self.path,
            "byte_count": self.byte_count,
            "sha256": self.sha256,
            "duration_ms": self.duration_ms,
        }


class SkillHostAdapter:
    """Native host behaviour for exactly one mounted Skill package.

    The adapter never searches, chunks, embeds, or preloads package content. Its
    telemetry is intentionally metadata-only: file paths, byte counts, digests,
    durations, and operation names -- never document content or SQL.
    """

    version = "skill-host-adapter-v0.1"
    _INSTRUCTION = "SKILL.md"

    def __init__(
        self,
        package_root: str | Path,
        target_config: dict[str, Any],
        *,
        host_revision: str,
        expected_host_revision: str | None = None,
    ) -> None:
        self._root = Path(package_root).resolve(strict=True)
        if not self._root.is_dir():
            raise SkillPackageError("Skill package root must be a directory")
        if not isinstance(host_revision, str) or not host_revision.strip():
            raise SkillPackageError("Skill host revision must be a non-empty immutable identifier")
        if expected_host_revision is not None and host_revision != expected_host_revision:
            raise SkillPackageError("Configured Skill host revision does not match runtime host revision")
        self._target_config = dict(target_config)
        self._host_revision = host_revision
        self._activated = False
        self._closed = False
        self._events: list[SkillAccessEvent] = []
        self._identity = self._validate_package()

    @property
    def identity(self) -> SkillIdentity:
        return self._identity

    @property
    def access_telemetry(self) -> tuple[dict[str, Any], ...]:
        return tuple(event.sanitized() for event in self._events)

    def preflight(self, deadline_seconds: float) -> Sequence[NativeResponse]:
        self._require_open()
        self._require_deadline(deadline_seconds)
        started = perf_counter()
        identity = self._validate_package()
        if identity != self._identity:
            raise SkillPackageError("Skill package identity changed after adapter construction")
        elapsed = self._elapsed(started)
        return (
            NativeResponse("ok", elapsed, {"operation": "skill.validate_package", **identity.discovery_metadata()}),
            NativeResponse("ok", 0.0, {"operation": "skill.confirm_discoverable", "name": identity.name}),
        )

    def public_tools(self) -> Sequence[dict[str, Any]]:
        self._require_open()
        # Discovery deliberately returns no document text or reference inventory.
        return (
            {
                "name": "skill.activate",
                "description": "Activate the discovered native Skill and load its SKILL.md instructions.",
                "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "name": "skill.read_reference",
                "description": "Read one referenced file after the native Skill is activated.",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        )

    def dispatch(self, request: NativeRequest) -> NativeResponse:
        self._require_open()
        self._require_deadline(request.deadline_seconds)
        assert_declared_operation(self._target_config, request.operation)
        if request.operation == "skill.activate":
            return self._activate(request.arguments)
        if request.operation == "skill.read_instruction":
            return self._read_instruction(request.arguments)
        if request.operation == "skill.read_reference":
            return self._read_reference(request.arguments)
        raise SkillHostError(f"Skill host does not implement declared operation: {request.operation}")

    def close(self) -> None:
        self._closed = True

    def _activate(self, arguments: dict[str, Any]) -> NativeResponse:
        self._reject_arguments(arguments)
        started = perf_counter()
        content, digest = self._read_regular(self._INSTRUCTION, allow_instruction=True)
        self._activated = True
        elapsed = self._elapsed(started)
        self._record("skill.activate", self._INSTRUCTION, len(content.encode("utf-8")), digest, elapsed)
        return NativeResponse(
            "ok",
            elapsed,
            {"identity": self._identity.discovery_metadata(), "instruction": content},
        )

    def _read_instruction(self, arguments: dict[str, Any]) -> NativeResponse:
        self._require_activated()
        if arguments not in ({}, {"path": self._INSTRUCTION}):
            raise SkillHostError("skill.read_instruction accepts only SKILL.md")
        started = perf_counter()
        content, digest = self._read_regular(self._INSTRUCTION, allow_instruction=True)
        elapsed = self._elapsed(started)
        self._record("skill.read_instruction", self._INSTRUCTION, len(content.encode("utf-8")), digest, elapsed)
        return NativeResponse("ok", elapsed, {"path": self._INSTRUCTION, "content": content})

    def _read_reference(self, arguments: dict[str, Any]) -> NativeResponse:
        self._require_activated()
        if set(arguments) != {"path"} or not isinstance(arguments["path"], str):
            raise SkillHostError("skill.read_reference requires exactly one string path")
        relative = arguments["path"]
        if relative == self._INSTRUCTION:
            raise SkillHostError("Read SKILL.md with skill.read_instruction or skill.activate")
        started = perf_counter()
        content, digest = self._read_regular(relative, allow_instruction=False)
        elapsed = self._elapsed(started)
        self._record("skill.read_reference", self._safe_path(relative), len(content.encode("utf-8")), digest, elapsed)
        return NativeResponse("ok", elapsed, {"path": self._safe_path(relative), "content": content})

    def _validate_package(self) -> SkillIdentity:
        skill_path = self._resolve_member(self._INSTRUCTION)
        content = self._read_utf8(skill_path)
        name, description = self._parse_frontmatter(content)
        entries: list[str] = []
        for path in sorted(self._root.rglob("*")):
            if path.is_symlink():
                raise SkillPackageError("Skill package must not contain symlinks")
            if path.is_file():
                relative = path.relative_to(self._root).as_posix()
                entries.append(f"{relative}:{self._sha256_bytes(path.read_bytes())}")
        if not entries:
            raise SkillPackageError("Skill package is empty")
        return SkillIdentity(
            name=name,
            description=description,
            package_sha256=self._sha256_bytes("\n".join(entries).encode("utf-8")),
            skill_md_sha256=self._sha256_bytes(content.encode("utf-8")),
            host_revision=self._host_revision,
        )

    def _read_regular(self, relative: str, *, allow_instruction: bool) -> tuple[str, str]:
        clean = self._safe_path(relative)
        if clean == self._INSTRUCTION and not allow_instruction:
            raise SkillHostError("SKILL.md is not a reference")
        path = self._resolve_member(clean)
        content = self._read_utf8(path)
        return content, self._sha256_bytes(content.encode("utf-8"))

    def _resolve_member(self, relative: str) -> Path:
        clean = self._safe_path(relative)
        candidate = self._root / clean
        if candidate.is_symlink():
            raise NativeIsolationError("Skill host refuses symlinked package members")
        resolved = candidate.resolve(strict=True)
        try:
            resolved.relative_to(self._root)
        except ValueError as exc:
            raise NativeIsolationError("Skill path escapes the mounted package") from exc
        if not resolved.is_file():
            raise SkillHostError("Skill path must name a regular file")
        return resolved

    @staticmethod
    def _safe_path(relative: str) -> str:
        normalized = relative.replace("\\", "/")
        path = PurePosixPath(normalized)
        if not normalized or path.is_absolute() or ".." in path.parts or "." in path.parts:
            raise NativeIsolationError("Skill paths must be package-relative and traversal-free")
        clean = path.as_posix()
        forbidden = ("benchmark/tpcds/results/gold", "evaluator-only", "orchestrator_only")
        if any(clean == item or clean.startswith(item + "/") for item in forbidden):
            raise NativeIsolationError("Skill host must not expose evaluator-only assets")
        return clean

    @staticmethod
    def _parse_frontmatter(content: str) -> tuple[str, str]:
        lines = content.splitlines()
        if len(lines) < 4 or lines[0] != "---":
            raise SkillPackageError("SKILL.md must start with YAML frontmatter")
        try:
            end = lines.index("---", 1)
        except ValueError as exc:
            raise SkillPackageError("SKILL.md frontmatter must be closed") from exc
        values: dict[str, str] = {}
        for line in lines[1:end]:
            key, separator, value = line.partition(":")
            if not separator or not key or not value.strip():
                raise SkillPackageError("SKILL.md frontmatter must contain simple key/value entries")
            values[key.strip()] = value.strip().strip('"')
        if not values.get("name") or not values.get("description"):
            raise SkillPackageError("SKILL.md frontmatter requires name and description")
        return values["name"], values["description"]

    @staticmethod
    def _read_utf8(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise SkillPackageError("Skill package members must be UTF-8 text") from exc

    @staticmethod
    def _sha256_bytes(value: bytes) -> str:
        return sha256(value).hexdigest()

    @staticmethod
    def _elapsed(started: float) -> float:
        return round((perf_counter() - started) * 1000, 3)

    @staticmethod
    def _require_deadline(deadline_seconds: float) -> None:
        if not isinstance(deadline_seconds, (int, float)) or deadline_seconds <= 0:
            raise SkillHostError("Skill host deadline_seconds must be positive")

    @staticmethod
    def _reject_arguments(arguments: dict[str, Any]) -> None:
        if arguments:
            raise SkillHostError("skill.activate accepts no arguments")

    def _require_open(self) -> None:
        if self._closed:
            raise SkillStateError("Skill host adapter is closed")

    def _require_activated(self) -> None:
        if not self._activated:
            raise SkillStateError("Activate the Skill before reading instructions or references")

    def _record(self, operation: str, path: str | None, byte_count: int, digest: str | None, duration_ms: float) -> None:
        self._events.append(SkillAccessEvent(operation, path, byte_count, digest, duration_ms))
