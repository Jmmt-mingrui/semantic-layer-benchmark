"""Factory for the six native benchmark target surfaces.

The factory unifies lifecycle mechanics only.  It does not normalize semantic
content: MetricFlow remains CLI-shaped, Ossie returns native YAML, OKF returns
original Markdown, and Skill retains progressive disclosure.  Database and
submission operations stay harness-owned and are added only when the registry
explicitly allows them.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from runner.adapters.metricflow import MetricFlowAdapter
from runner.adapters.ossie import OssieAdapter
from runner.adapters.skill_host import SkillHostAdapter
from runner.core.control_tools import ControlToolDispatcher
from runner.core.native_adapter import NativeAdapter, NativeRequest, NativeResponse
from runner.core.okf_native_consumer import OkfNativeConsumer


class NativeFactoryError(RuntimeError):
    pass


SUPPORTED_TARGETS = (
    "blank_context",
    "ddl_only",
    "metricflow",
    "ossie",
    "okf",
    "skill",
)

_HARNESS_OPERATIONS = frozenset(
    {"db.list_relations", "db.describe_relations", "db.execute_readonly", "benchmark.submit_result"}
)

# Some existing native adapters predate JSON-schema tool publication.  These
# schemas describe only their original argument shapes; they do not create a
# shared semantic request format.
_NATIVE_ARGUMENT_SCHEMAS: dict[str, dict[str, Any]] = {
    "okf.list_files": {
        "type": "object",
        "properties": {"prefix": {"type": "string"}},
        "additionalProperties": False,
    },
    "okf.read_file": {
        "type": "object",
        "required": ["path"],
        "properties": {"path": {"type": "string", "minLength": 1}},
        "additionalProperties": False,
    },
    "okf.follow_link": {
        "type": "object",
        "required": ["source_path", "link"],
        "properties": {
            "source_path": {"type": "string", "minLength": 1},
            "link": {"type": "string", "minLength": 1},
        },
        "additionalProperties": False,
    },
    "okf.search_text": {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        },
        "additionalProperties": False,
    },
}


def _artifact_id(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _hash_tree(root: Path) -> str | None:
    if not root.exists():
        return None
    entries: list[str] = []
    paths = [root] if root.is_file() else sorted(path for path in root.rglob("*") if path.is_file())
    for path in paths:
        if path.is_symlink():
            raise NativeFactoryError(f"Native artifact tree contains a symlink: {path}")
        relative = path.name if root.is_file() else path.relative_to(root).as_posix()
        entries.append(f"{relative}:{sha256(path.read_bytes()).hexdigest()}")
    return sha256("\n".join(entries).encode("utf-8")).hexdigest()


def _ddl_context(root: Path) -> tuple[str, str]:
    paths = sorted(root.rglob("*.sql"))
    if not paths:
        raise NativeFactoryError(f"No physical DDL found under {root}")
    sections = [f"-- Source: {path.name}\n{path.read_text(encoding='utf-8').rstrip()}" for path in paths]
    content = "\n\n".join(sections) + "\n"
    return content, sha256(content.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class NativeFactorySettings:
    metricflow_runtime_project_dir: Path | None = None
    metricflow_executable: str = "mf"
    skill_host_revision: str | None = None


class NativeRuntime:
    """One target runtime created for exactly one trial."""

    def __init__(
        self,
        *,
        target: str,
        target_config: Mapping[str, Any],
        harness: ControlToolDispatcher,
        native_adapter: NativeAdapter | None,
        initial_context: str | None,
        artifact_sha256: str | None,
    ) -> None:
        self.target = target
        self.target_config = dict(target_config)
        self.harness = harness
        self.native_adapter = native_adapter
        self.initial_context = initial_context
        self.artifact_sha256 = artifact_sha256
        self._closed = False

    @property
    def adapter_version(self) -> str:
        if self.native_adapter is None:
            return "harness-native-v0.1"
        return str(getattr(self.native_adapter, "version", self.native_adapter.__class__.__name__))

    def preflight(self, deadline_seconds: float) -> tuple[NativeResponse, ...]:
        if self._closed:
            raise NativeFactoryError("Native runtime is closed")
        if self.native_adapter is None:
            return ()
        return tuple(self.native_adapter.preflight(deadline_seconds))

    def public_tools(self) -> tuple[dict[str, Any], ...]:
        if self._closed:
            raise NativeFactoryError("Native runtime is closed")
        allowed = set(self.target_config.get("allowed_operations", ()))
        tools: list[dict[str, Any]] = []
        if self.native_adapter is not None:
            for raw in self.native_adapter.public_tools():
                name = raw.get("name")
                if name not in allowed:
                    continue
                tool = dict(raw)
                if not isinstance(tool.get("input_schema"), Mapping):
                    tool["input_schema"] = _NATIVE_ARGUMENT_SCHEMAS.get(
                        str(name), {"type": "object", "additionalProperties": False}
                    )
                tools.append(tool)
        for tool in self.harness.public_tools():
            if tool["name"] in allowed:
                tools.append(tool)
        names = [str(tool["name"]) for tool in tools]
        if len(names) != len(set(names)):
            raise NativeFactoryError(f"Duplicate public tool names for {self.target}: {names}")
        undeclared = set(names) - allowed
        if undeclared:
            raise NativeFactoryError(f"Runtime exposed undeclared tools: {sorted(undeclared)}")
        return tuple(tools)

    def dispatch(self, request: NativeRequest) -> NativeResponse:
        if self._closed:
            raise NativeFactoryError("Native runtime is closed")
        allowed = set(self.target_config.get("allowed_operations", ()))
        if request.operation not in allowed:
            # Let the shared native assertion machinery classify Gold separately
            # when a native adapter exists; otherwise fail closed here.
            from runner.core.native_adapter import assert_declared_operation

            assert_declared_operation(self.target_config, request.operation)
        if request.operation in _HARNESS_OPERATIONS:
            outcome = self.harness.dispatch(request.operation, request.arguments)
            request_payload = {"operation": request.operation, "arguments": request.arguments}
            response_payload = {"operation": request.operation, "output": outcome.output}
            return NativeResponse(
                status="ok",
                duration_ms=outcome.duration_ms,
                output=outcome.output,
                request_artifact=_artifact_id(request_payload),
                response_artifact=_artifact_id(response_payload),
            )
        if self.native_adapter is None:
            raise NativeFactoryError(f"No native adapter owns operation {request.operation}")
        return self.native_adapter.dispatch(request)

    @property
    def database_calls(self) -> int:
        return int(self.harness.database_attempts)

    @property
    def submission(self) -> dict[str, Any] | None:
        return self.harness.submission

    @property
    def results(self) -> Mapping[str, Any]:
        return self.harness.results

    @property
    def sql_by_handle(self) -> Mapping[str, str]:
        return self.harness.sql_by_handle

    def close(self) -> None:
        if self._closed:
            return
        if self.native_adapter is not None:
            self.native_adapter.close()
        self._closed = True


AdapterOverride = Callable[[dict[str, Any], Path, NativeFactorySettings], NativeAdapter]


class NativeAdapterFactory:
    """Build an isolated native runtime from the target registry."""

    def __init__(
        self,
        *,
        root: str | Path,
        registry: Mapping[str, Any],
        database: Any,
        tool_catalog: Mapping[str, Any],
        settings: NativeFactorySettings | None = None,
        adapter_overrides: Mapping[str, AdapterOverride] | None = None,
        max_database_attempts: int = 3,
        database_timeout_seconds: float = 120,
    ) -> None:
        self.root = Path(root).resolve()
        self.registry = dict(registry)
        self.database = database
        self.tool_catalog = dict(tool_catalog)
        self.settings = settings or NativeFactorySettings()
        self.adapter_overrides = dict(adapter_overrides or {})
        self.max_database_attempts = max_database_attempts
        self.database_timeout_seconds = database_timeout_seconds

    def create(self, target: str) -> NativeRuntime:
        if target not in SUPPORTED_TARGETS:
            raise NativeFactoryError(f"Unified native runner does not support target {target!r}")
        try:
            config = dict(self.registry["targets"][target])
        except (KeyError, TypeError) as error:
            raise NativeFactoryError(f"Target is missing from registry: {target}") from error
        allowed = set(config.get("allowed_operations", ()))
        harness_allowed = allowed & _HARNESS_OPERATIONS
        harness = ControlToolDispatcher(
            self.database,
            self.tool_catalog,
            harness_allowed,
            max_database_attempts=self.max_database_attempts,
            database_timeout_seconds=self.database_timeout_seconds,
        )
        surface = config.get("native_surface", {})
        artifact_root_value = surface.get("artifact_root") if isinstance(surface, Mapping) else None
        artifact_root = self.root / artifact_root_value if isinstance(artifact_root_value, str) else None
        artifact_hash = _hash_tree(artifact_root) if artifact_root is not None else None
        initial_context: str | None = None
        adapter: NativeAdapter | None = None

        if target == "ddl_only":
            if artifact_root is None:
                raise NativeFactoryError("DDL-only target requires an artifact root")
            ddl, artifact_hash = _ddl_context(artifact_root)
            initial_context = "Physical database DDL for this trial:\n\n" + ddl
        elif target not in {"blank_context"}:
            if artifact_root is None:
                raise NativeFactoryError(f"{target} requires a native artifact root")
            override = self.adapter_overrides.get(target)
            if override is not None:
                adapter = override(config, artifact_root, self.settings)
            elif target == "metricflow":
                runtime = self.settings.metricflow_runtime_project_dir
                if runtime is None:
                    raise NativeFactoryError("MetricFlow requires metricflow_runtime_project_dir")
                adapter = MetricFlowAdapter(
                    target_config=config,
                    model_root=artifact_root,
                    runtime_project_dir=runtime,
                    executable=self.settings.metricflow_executable,
                )
            elif target == "ossie":
                adapter = OssieAdapter(target_config=config, model_root=artifact_root)
            elif target == "okf":
                adapter = OkfNativeConsumer(artifact_root, config)
            elif target == "skill":
                revision = self.settings.skill_host_revision
                if not revision:
                    raise NativeFactoryError("Skill requires an immutable skill_host_revision")
                adapter = SkillHostAdapter(artifact_root, config, host_revision=revision)
                identity = adapter.identity.discovery_metadata()
                initial_context = (
                    "Discovered native Skill metadata (instructions are not preloaded):\n"
                    + json.dumps(identity, ensure_ascii=False, sort_keys=True)
                )

        return NativeRuntime(
            target=target,
            target_config=config,
            harness=harness,
            native_adapter=adapter,
            initial_context=initial_context,
            artifact_sha256=artifact_hash,
        )
