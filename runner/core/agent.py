from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence


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


@dataclass(frozen=True)
class AgentTurn:
    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    usage: AgentUsage = field(default_factory=AgentUsage)
    response_id: str | None = None


class AgentProvider(Protocol):
    """One provider call with no hidden cross-trial state."""

    def complete(
        self,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        generation: dict[str, Any],
        timeout_seconds: float,
    ) -> AgentTurn: ...


class ScriptedAgentProvider:
    """Deterministic provider used for contract tests and offline smoke runs."""

    def __init__(self, turns: Sequence[AgentTurn]):
        self._turns = tuple(turns)
        self._index = 0
        self.calls: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []

    def complete(
        self,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        generation: dict[str, Any],
        timeout_seconds: float,
    ) -> AgentTurn:
        del generation, timeout_seconds
        self.calls.append((list(messages), list(tools)))
        if self._index >= len(self._turns):
            raise RuntimeError("Scripted agent exhausted before result submission")
        turn = self._turns[self._index]
        self._index += 1
        return turn
