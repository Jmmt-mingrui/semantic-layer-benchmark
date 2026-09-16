from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence


class AgentProviderError(RuntimeError):
    """A provider transport or response failure, distinct from agent protocol errors."""


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class AgentUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None
    provider_reported: bool | None = None


def usage_payload(usage: AgentUsage) -> dict[str, int | bool | None]:
    """Return schema-shaped provider usage without estimating missing values."""

    reported = usage.provider_reported
    if reported is None:
        reported = any(
            value is not None
            for value in (
                usage.input_tokens,
                usage.output_tokens,
                usage.cached_input_tokens,
                usage.reasoning_tokens,
            )
        )
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cached_input_tokens": usage.cached_input_tokens,
        "reasoning_tokens": usage.reasoning_tokens,
        "provider_reported": reported,
    }


def sum_usage_field(usages: Sequence[AgentUsage], field: str) -> int | None:
    """Sum a token field only when every completed provider turn reports it."""

    values = [getattr(usage, field) for usage in usages]
    if not values or any(value is None for value in values):
        return None
    return sum(int(value) for value in values)


@dataclass(frozen=True)
class AgentTurn:
    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    usage: AgentUsage = field(default_factory=AgentUsage)
    response_id: str | None = None


class AgentProvider(Protocol):
    """One stateless provider boundary used inside exactly one fresh trial."""

    provider_kind: str
    ranking_eligible: bool

    def complete(
        self,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        generation: dict[str, Any],
        timeout_seconds: float,
    ) -> AgentTurn: ...

    @property
    def retry_count(self) -> int: ...


class ScriptedAgentProvider:
    """Deterministic provider for CI protocol tests, never benchmark ranking."""

    provider_kind = "scripted"
    ranking_eligible = False

    def __init__(self, turns: Sequence[AgentTurn]):
        self._turns = tuple(turns)
        self._index = 0
        self.calls: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []

    @property
    def retry_count(self) -> int:
        return 0

    def complete(
        self,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        generation: dict[str, Any],
        timeout_seconds: float,
    ) -> AgentTurn:
        del generation, timeout_seconds
        # Keep an immutable snapshot of what this fresh provider instance saw.
        self.calls.append((list(messages), list(tools)))
        if self._index >= len(self._turns):
            raise RuntimeError("Scripted agent exhausted before result submission")
        turn = self._turns[self._index]
        self._index += 1
        return turn
