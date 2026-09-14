"""Stateless live Agent provider boundary.

The benchmark owns conversation state.  This module performs one HTTP request
per ``complete`` call and never stores provider messages, server-side thread IDs,
or hidden reasoning.  It intentionally accepts a configurable Chat-Completions-
compatible endpoint so provider, model, generation parameters, authentication,
and timeouts remain experiment inputs instead of source-code constants.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import time
from typing import Any, Callable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from runner.core.agent import AgentTurn, AgentUsage, ToolCall


class LiveProviderError(RuntimeError):
    """Raised when a configured live provider cannot complete a turn."""


@dataclass(frozen=True)
class LiveProviderSettings:
    provider: str
    model: str
    endpoint: str
    api_key: str | None = None
    api_key_env: str | None = None
    authorization_scheme: str = "Bearer"
    max_retries: int = 2
    retry_backoff_seconds: float = 0.5
    max_tokens_field: str = "max_tokens"
    extra_headers: Mapping[str, str] | None = None

    def resolved_api_key(self) -> str | None:
        if self.api_key is not None:
            return self.api_key
        if self.api_key_env:
            value = os.getenv(self.api_key_env)
            if value:
                return value
        return None


Transport = Callable[[str, bytes, Mapping[str, str], float], tuple[int, bytes]]
Sleep = Callable[[float], None]


def _http_transport(url: str, body: bytes, headers: Mapping[str, str], timeout_seconds: float) -> tuple[int, bytes]:
    request = Request(url, data=body, headers=dict(headers), method="POST")
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - endpoint is explicit benchmark config
        return int(response.status), response.read()


def _validate_endpoint(endpoint: str, *, credentialed: bool) -> None:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise LiveProviderError("endpoint must be an absolute http(s) URL")
    if not credentialed:
        return
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        return
    raise LiveProviderError(
        "credentialed provider endpoints must use HTTPS; plain HTTP is allowed only for localhost development"
    )


def _tool_for_provider(tool: Mapping[str, Any]) -> dict[str, Any]:
    name = tool.get("name")
    if not isinstance(name, str) or not name:
        raise LiveProviderError("Every exposed tool must have a non-empty name")
    schema = tool.get("input_schema")
    if not isinstance(schema, Mapping):
        schema = {"type": "object", "additionalProperties": True}
    function: dict[str, Any] = {"name": name, "parameters": dict(schema)}
    description = tool.get("description")
    if isinstance(description, str) and description:
        function["description"] = description
    return {"type": "function", "function": function}


def _usage(document: Mapping[str, Any]) -> AgentUsage:
    raw = document.get("usage")
    if not isinstance(raw, Mapping):
        return AgentUsage()
    details = raw.get("prompt_tokens_details")
    cached: Any = raw.get("cached_input_tokens")
    if cached is None and isinstance(details, Mapping):
        cached = details.get("cached_tokens")
    return AgentUsage(
        input_tokens=_optional_int(raw.get("input_tokens", raw.get("prompt_tokens"))),
        output_tokens=_optional_int(raw.get("output_tokens", raw.get("completion_tokens"))),
        cached_input_tokens=_optional_int(cached),
    )


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


class LiveAgentProvider:
    """One stateless live provider used by one benchmark trial.

    A runner must construct a new instance per trial.  The instance retains only
    operational counters (attempts/retries); conversation content is supplied by
    the caller on every turn and is never cached here.
    """

    provider_kind = "live"
    ranking_eligible = True

    def __init__(
        self,
        settings: LiveProviderSettings,
        *,
        transport: Transport = _http_transport,
        sleep: Sleep = time.sleep,
    ) -> None:
        if not settings.provider or not settings.model or not settings.endpoint:
            raise LiveProviderError("provider, model, and endpoint are required")
        if settings.max_retries < 0:
            raise LiveProviderError("max_retries must be non-negative")
        _validate_endpoint(settings.endpoint, credentialed=settings.resolved_api_key() is not None)
        self.settings = settings
        self._transport = transport
        self._sleep = sleep
        self._retry_count = 0
        self._request_count = 0

    @property
    def retry_count(self) -> int:
        return self._retry_count

    @property
    def request_count(self) -> int:
        return self._request_count

    def complete(
        self,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        generation: dict[str, Any],
        timeout_seconds: float,
    ) -> AgentTurn:
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise LiveProviderError("timeout_seconds must be positive")
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": list(messages),
        }
        if tools:
            payload["tools"] = [_tool_for_provider(tool) for tool in tools]
            payload["tool_choice"] = "auto"
        if "temperature" in generation and generation["temperature"] is not None:
            payload["temperature"] = generation["temperature"]
        if "max_output_tokens" in generation and generation["max_output_tokens"] is not None:
            payload[self.settings.max_tokens_field] = generation["max_output_tokens"]
        if "seed" in generation and generation["seed"] is not None:
            payload["seed"] = generation["seed"]
        if generation.get("parallel_tool_calls") is not None and tools:
            payload["parallel_tool_calls"] = bool(generation["parallel_tool_calls"])

        headers = {"Content-Type": "application/json"}
        key = self.settings.resolved_api_key()
        if key:
            headers["Authorization"] = f"{self.settings.authorization_scheme} {key}".strip()
        if self.settings.extra_headers:
            headers.update(dict(self.settings.extra_headers))
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            self._request_count += 1
            try:
                status, raw = self._transport(self.settings.endpoint, body, headers, float(timeout_seconds))
                if status >= 500 or status == 429:
                    raise LiveProviderError(f"provider returned retryable HTTP status {status}")
                if not 200 <= status < 300:
                    raise LiveProviderError(f"provider returned HTTP status {status}")
                return self._parse_response(raw)
            except HTTPError as error:
                last_error = error
                retryable = error.code == 429 or error.code >= 500
                if not retryable or attempt >= self.settings.max_retries:
                    raise LiveProviderError(f"provider HTTP error {error.code}") from error
            except (URLError, TimeoutError, LiveProviderError) as error:
                last_error = error
                if isinstance(error, LiveProviderError) and "retryable" not in str(error):
                    raise
                if attempt >= self.settings.max_retries:
                    break
            self._retry_count += 1
            self._sleep(self.settings.retry_backoff_seconds * (2**attempt))
        raise LiveProviderError(f"live provider failed after retries: {last_error}") from last_error

    @staticmethod
    def _parse_response(raw: bytes) -> AgentTurn:
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LiveProviderError("provider returned invalid JSON") from error
        choices = document.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], Mapping):
            raise LiveProviderError("provider response has no choices[0]")
        message = choices[0].get("message")
        if not isinstance(message, Mapping):
            raise LiveProviderError("provider response has no assistant message")
        tool_calls: list[ToolCall] = []
        for index, raw_call in enumerate(message.get("tool_calls") or []):
            if not isinstance(raw_call, Mapping):
                raise LiveProviderError("provider tool call must be an object")
            function = raw_call.get("function")
            if not isinstance(function, Mapping) or not isinstance(function.get("name"), str):
                raise LiveProviderError("provider tool call is missing function.name")
            arguments = function.get("arguments", "{}")
            if isinstance(arguments, str):
                try:
                    parsed_arguments = json.loads(arguments)
                except json.JSONDecodeError as error:
                    raise LiveProviderError("provider tool arguments are not valid JSON") from error
            elif isinstance(arguments, Mapping):
                parsed_arguments = dict(arguments)
            else:
                raise LiveProviderError("provider tool arguments must be JSON object text")
            if not isinstance(parsed_arguments, dict):
                raise LiveProviderError("provider tool arguments must decode to an object")
            tool_calls.append(
                ToolCall(
                    id=str(raw_call.get("id") or f"call-{index + 1:03d}"),
                    name=str(function["name"]),
                    arguments=parsed_arguments,
                )
            )
        content = message.get("content")
        if content is not None and not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
        response_id = document.get("id")
        return AgentTurn(
            content=content,
            tool_calls=tuple(tool_calls),
            usage=_usage(document),
            response_id=str(response_id) if response_id is not None else None,
        )
