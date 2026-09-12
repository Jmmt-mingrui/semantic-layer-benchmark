from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence


class NativeAdapterError(RuntimeError):
    """Base error for a target's native runtime boundary."""


class NativeOperationError(NativeAdapterError):
    """Raised when a target attempts an undeclared operation."""


class NativeIsolationError(NativeAdapterError):
    """Raised when an adapter is configured to expose evaluator-only assets."""


@dataclass(frozen=True)
class TargetQuestion:
    """The only question representation that may cross into target code."""

    question_id: str
    instance_id: str
    prompt: str

    @classmethod
    def from_instance(cls, instance: dict[str, Any]) -> "TargetQuestion":
        target_input = instance.get("target_input")
        if not isinstance(target_input, dict) or set(target_input) != {"question"}:
            raise NativeIsolationError("Target input must contain exactly the materialized question")
        prompt = target_input["question"]
        if not isinstance(prompt, str) or not prompt.strip():
            raise NativeIsolationError("Target question prompt must be a non-empty string")
        return cls(
            question_id=str(instance["question_id"]),
            instance_id=str(instance["instance_id"]),
            prompt=prompt,
        )

    def provider_context(self) -> dict[str, str]:
        return {
            "question_id": self.question_id,
            "instance_id": self.instance_id,
            "question": self.prompt,
        }


@dataclass(frozen=True)
class NativeRequest:
    operation: str
    arguments: dict[str, Any]
    deadline_seconds: float


@dataclass(frozen=True)
class NativeResponse:
    status: str
    duration_ms: float
    output: dict[str, Any]
    request_artifact: str | None = None
    response_artifact: str | None = None


class NativeAdapter(Protocol):
    """Closed, target-specific native surface.

    Adapters expose original target operation names and payloads. They must not
    create a shared semantic API, direct-SQL fallback, or evaluator access.
    """

    version: str

    def preflight(self, deadline_seconds: float) -> Sequence[NativeResponse]: ...

    def public_tools(self) -> Sequence[dict[str, Any]]: ...

    def dispatch(self, request: NativeRequest) -> NativeResponse: ...

    def close(self) -> None: ...


def assert_declared_operation(target_config: dict[str, Any], operation: str) -> None:
    prohibited = set(target_config.get("prohibited_operations", []))
    allowed = set(target_config.get("allowed_operations", []))
    if operation == "benchmark.read_gold" or operation in prohibited:
        raise NativeIsolationError(f"Prohibited native operation: {operation}")
    if operation not in allowed:
        raise NativeOperationError(f"Undeclared native operation: {operation}")


def assert_native_artifact_root(root: str | None) -> None:
    """Reject evaluator-only roots before an adapter is started."""

    if root is None:
        return
    normalized = root.replace("\\", "/").strip("/")
    forbidden = (
        "benchmark/tpcds/results/gold",
        "benchmark/tpcds/questions/instances/evaluator-only",
    )
    if any(normalized == value or normalized.startswith(value + "/") for value in forbidden):
        raise NativeIsolationError("Native artifact roots must not expose evaluator-only assets")
