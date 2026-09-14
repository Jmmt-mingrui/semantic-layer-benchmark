"""Pinned MetricFlow CLI adapter.

This adapter deliberately shells out only to the MetricFlow CLI surface pinned
by ``targets.native.yaml``. It never imports MetricFlow internals, generates
SQL, or opens a database connection itself.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from runner.core.native_adapter import (
    NativeAdapterError,
    NativeRequest,
    NativeResponse,
    assert_declared_operation,
    assert_native_artifact_root,
)


METRICFLOW_CLI_VERSION = "0.213.0.dev0"
"""The package version at the pinned MetricFlow source revision 8750c1d."""


class MetricFlowConfigurationError(NativeAdapterError):
    """Raised for an invalid local MetricFlow adapter configuration."""


class MetricFlowPreflightError(NativeAdapterError):
    """Raised when execution is attempted before successful preflight."""


@dataclass(frozen=True)
class CommandResult:
    """Minimal subprocess result retained by the adapter telemetry boundary."""

    returncode: int
    stdout: str = ""
    stderr: str = ""


CommandRunner = Callable[[Sequence[str], Path, float], CommandResult]


def run_subprocess(argv: Sequence[str], cwd: Path, timeout_seconds: float) -> CommandResult:
    """Execute one CLI request without a shell or a database fallback."""

    completed = subprocess.run(
        list(argv),
        cwd=cwd,
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout_seconds,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _artifact_id(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _as_non_empty_strings(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
        raise MetricFlowConfigurationError(f"{name} must be a non-empty list of strings")
    return list(value)


def _as_optional_string(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise MetricFlowConfigurationError(f"{name} must be a non-empty string when provided")
    return value


class MetricFlowAdapter:
    """Closed adapter for the pinned, documented MetricFlow CLI.

    The executable runtime directory must be an externally provisioned dbt
    project compatible with MetricFlow 0.213.0.dev0. The source semantic-model
    root is kept separate so a benchmark run can record both identities.
    """

    version = METRICFLOW_CLI_VERSION

    _native_operations = frozenset(
        {
            "metricflow.list_metrics",
            "metricflow.list_dimensions",
            "metricflow.list_dimension_values",
            "metricflow.list_entities",
            "metricflow.query",
        }
    )

    def __init__(
        self,
        *,
        target_config: Mapping[str, Any],
        model_root: str | Path,
        runtime_project_dir: str | Path,
        executable: str = "mf",
        required_version: str = METRICFLOW_CLI_VERSION,
        command_runner: CommandRunner = run_subprocess,
    ) -> None:
        self._target_config = dict(target_config)
        self._model_root = Path(model_root)
        self._runtime_project_dir = Path(runtime_project_dir)
        self._executable = executable
        self._required_version = required_version
        self._command_runner = command_runner
        self._ready = False
        self._closed = False

        if self._target_config.get("role") != "executable_semantic_engine":
            raise MetricFlowConfigurationError("MetricFlow target must be an executable semantic engine")
        if self._target_config.get("native_surface", {}).get("name") != "self_hosted_metricflow_cli":
            raise MetricFlowConfigurationError("MetricFlow target must declare self_hosted_metricflow_cli")
        assert_native_artifact_root(self._target_config.get("native_surface", {}).get("artifact_root"))
        if not isinstance(executable, str) or not executable:
            raise MetricFlowConfigurationError("MetricFlow executable must be a non-empty string")
        if not isinstance(required_version, str) or not required_version:
            raise MetricFlowConfigurationError("MetricFlow required_version must be a non-empty string")

    def public_tools(self) -> Sequence[dict[str, Any]]:
        """Return only documented MetricFlow operations, never SQL tools.

        ``benchmark.submit_result`` remains a harness operation. It is declared
        in the target registry but is intentionally not a MetricFlow CLI tool.
        """

        return (
            {"name": "metricflow.list_metrics", "input_schema": {"type": "object", "additionalProperties": False}},
            {
                "name": "metricflow.list_dimensions",
                "input_schema": {
                    "type": "object",
                    "required": ["metrics"],
                    "properties": {"metrics": {"type": "array", "minItems": 1, "items": {"type": "string"}}},
                    "additionalProperties": False,
                },
            },
            {
                "name": "metricflow.list_dimension_values",
                "input_schema": {
                    "type": "object",
                    "required": ["metrics", "dimension"],
                    "properties": {
                        "metrics": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                        "dimension": {"type": "string"},
                        "start_time": {"type": "string"},
                        "end_time": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
            },
            {
                "name": "metricflow.list_entities",
                "input_schema": {
                    "type": "object",
                    "required": ["metrics"],
                    "properties": {"metrics": {"type": "array", "minItems": 1, "items": {"type": "string"}}},
                    "additionalProperties": False,
                },
            },
            {
                "name": "metricflow.query",
                "input_schema": {
                    "type": "object",
                    "required": ["metrics"],
                    "properties": {
                        "metrics": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                        "group_by": {"type": "array", "items": {"type": "string"}},
                        "where": {"type": "array", "items": {"type": "string"}},
                        "start_time": {"type": "string"},
                        "end_time": {"type": "string"},
                        "order": {"type": "array", "items": {"type": "string"}},
                        "limit": {"type": "integer", "minimum": 1},
                    },
                    "additionalProperties": False,
                },
            },
        )

    def preflight(self, deadline_seconds: float) -> Sequence[NativeResponse]:
        """Verify the pinned CLI, source layout, warehouse health, and configs.

        A failed preflight leaves the adapter closed for dispatch. This makes an
        unavailable native engine observable rather than silently routing the
        condition through database SQL.
        """

        self._ensure_open()
        self._validate_deadline(deadline_seconds)
        self._ready = False

        version_response = self._invoke("metricflow.version_probe", [self._executable, "--version"], deadline_seconds)
        if version_response.status != "succeeded" or self._required_version not in version_response.output["stdout"]:
            return (version_response, self._local_failure("metricflow.model_layout", "version_mismatch_or_unavailable"))

        layout_response = self._validate_model_layout()
        if layout_response.status != "succeeded":
            return (version_response, layout_response)

        health_response = self._invoke(
            "metricflow.health_checks", [self._executable, "health-checks"], deadline_seconds
        )
        if health_response.status != "succeeded":
            return (version_response, layout_response, health_response)

        validation_response = self._invoke(
            "metricflow.validate_configs", [self._executable, "validate-configs"], deadline_seconds
        )
        if validation_response.status == "succeeded":
            self._ready = True
        return (version_response, layout_response, health_response, validation_response)

    def dispatch(self, request: NativeRequest) -> NativeResponse:
        self._ensure_open()
        self._validate_deadline(request.deadline_seconds)
        assert_declared_operation(self._target_config, request.operation)
        if request.operation not in self._native_operations:
            raise MetricFlowConfigurationError(f"MetricFlow adapter cannot dispatch harness operation: {request.operation}")
        if not self._ready:
            raise MetricFlowPreflightError("MetricFlow preflight must succeed before dispatch")
        argv = self._command_for(request.operation, request.arguments)
        return self._invoke(request.operation, argv, request.deadline_seconds)

    def close(self) -> None:
        self._closed = True
        self._ready = False

    def _ensure_open(self) -> None:
        if self._closed:
            raise MetricFlowPreflightError("MetricFlow adapter is closed")

    @staticmethod
    def _validate_deadline(deadline_seconds: float) -> None:
        if not isinstance(deadline_seconds, (int, float)) or deadline_seconds <= 0:
            raise MetricFlowConfigurationError("deadline_seconds must be positive")

    def _validate_model_layout(self) -> NativeResponse:
        required = (
            self._model_root / "project_configuration.yml",
            self._model_root / "semantic_models",
            self._runtime_project_dir / "dbt_project.yml",
        )
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            return self._local_failure("metricflow.model_layout", "missing_required_model_or_runtime_path", {"missing": missing})
        payload = {
            "native_operation": "metricflow.model_layout",
            "model_root": str(self._model_root),
            "runtime_project_dir": str(self._runtime_project_dir),
            "required_paths": [str(path) for path in required],
        }
        return NativeResponse(
            status="succeeded",
            duration_ms=0.0,
            output=payload,
            request_artifact=_artifact_id(payload),
            response_artifact=_artifact_id({"status": "succeeded", "missing": []}),
        )

    def _local_failure(self, operation: str, error_type: str, extra: Mapping[str, Any] | None = None) -> NativeResponse:
        payload: dict[str, Any] = {"native_operation": operation, "error_type": error_type}
        if extra:
            payload.update(extra)
        return NativeResponse(
            status="failed",
            duration_ms=0.0,
            output=payload,
            request_artifact=_artifact_id({"native_operation": operation}),
            response_artifact=_artifact_id({"status": "failed", **payload}),
        )

    def _invoke(self, operation: str, argv: list[str], deadline_seconds: float) -> NativeResponse:
        request_payload = {"native_operation": operation, "argv": argv, "cwd": str(self._runtime_project_dir)}
        started = time.perf_counter()
        try:
            result = self._command_runner(argv, self._runtime_project_dir, deadline_seconds)
            duration_ms = (time.perf_counter() - started) * 1000
        except FileNotFoundError as error:
            return self._failure_from_exception(request_payload, "executable_not_found", str(error), started)
        except subprocess.TimeoutExpired as error:
            return self._failure_from_exception(request_payload, "timeout", str(error), started)
        except OSError as error:
            return self._failure_from_exception(request_payload, "subprocess_error", str(error), started)

        status = "succeeded" if result.returncode == 0 else self._classify_failure(result.stderr)
        output = {
            **request_payload,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        return NativeResponse(
            status=status,
            duration_ms=duration_ms,
            output=output,
            request_artifact=_artifact_id(request_payload),
            response_artifact=_artifact_id({"status": status, **output}),
        )

    def _failure_from_exception(
        self, request_payload: Mapping[str, Any], error_type: str, detail: str, started: float
    ) -> NativeResponse:
        output = {**request_payload, "error_type": error_type, "detail": detail}
        return NativeResponse(
            status="failed",
            duration_ms=(time.perf_counter() - started) * 1000,
            output=output,
            request_artifact=_artifact_id(request_payload),
            response_artifact=_artifact_id({"status": "failed", **output}),
        )

    @staticmethod
    def _classify_failure(stderr: str) -> str:
        normalized = stderr.lower()
        semantic_terms = ("metric", "dimension", "entity")
        unsupported_terms = ("not found", "not available", "unknown", "unsupported")
        if any(term in normalized for term in semantic_terms) and any(term in normalized for term in unsupported_terms):
            return "unsupported"
        return "failed"

    def _command_for(self, operation: str, arguments: Mapping[str, Any]) -> list[str]:
        if not isinstance(arguments, Mapping):
            raise MetricFlowConfigurationError("MetricFlow arguments must be an object")
        args = dict(arguments)
        if operation == "metricflow.list_metrics":
            self._reject_extra(args, set())
            return [self._executable, "list", "metrics"]
        if operation == "metricflow.list_dimensions":
            self._reject_extra(args, {"metrics"})
            return [self._executable, "list", "dimensions", "--metrics", ",".join(_as_non_empty_strings(args["metrics"], "metrics"))]
        if operation == "metricflow.list_entities":
            self._reject_extra(args, {"metrics"})
            return [self._executable, "list", "entities", "--metrics", ",".join(_as_non_empty_strings(args["metrics"], "metrics"))]
        if operation == "metricflow.list_dimension_values":
            self._reject_extra(args, {"metrics", "dimension", "start_time", "end_time"})
            dimension = _as_optional_string(args.get("dimension"), "dimension")
            if dimension is None:
                raise MetricFlowConfigurationError("dimension is required")
            command = [
                self._executable,
                "list",
                "dimension-values",
                "--metrics",
                ",".join(_as_non_empty_strings(args.get("metrics"), "metrics")),
                "--dimension",
                dimension,
            ]
            return self._with_time_bounds(command, args)
        if operation == "metricflow.query":
            self._reject_extra(args, {"metrics", "group_by", "where", "start_time", "end_time", "order", "limit"})
            command = [self._executable, "query", "--metrics", ",".join(_as_non_empty_strings(args.get("metrics"), "metrics"))]
            for flag, name in (("--group-by", "group_by"), ("--order", "order")):
                if name in args:
                    command.extend([flag, ",".join(_as_non_empty_strings(args[name], name))])
            if "where" in args:
                for where in _as_non_empty_strings(args["where"], "where"):
                    command.extend(["--where", where])
            command = self._with_time_bounds(command, args)
            if "limit" in args:
                limit = args["limit"]
                if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
                    raise MetricFlowConfigurationError("limit must be a positive integer")
                command.extend(["--limit", str(limit)])
            return command
        raise MetricFlowConfigurationError(f"No MetricFlow command mapping for {operation}")

    @staticmethod
    def _reject_extra(arguments: Mapping[str, Any], allowed: set[str]) -> None:
        extra = set(arguments) - allowed
        if extra:
            raise MetricFlowConfigurationError(f"Unsupported MetricFlow argument(s): {', '.join(sorted(extra))}")

    @staticmethod
    def _with_time_bounds(command: list[str], arguments: Mapping[str, Any]) -> list[str]:
        for flag, name in (("--start-time", "start_time"), ("--end-time", "end_time")):
            value = _as_optional_string(arguments.get(name), name)
            if value is not None:
                command.extend([flag, value])
        return command
