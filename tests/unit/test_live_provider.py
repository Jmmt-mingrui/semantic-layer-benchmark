from __future__ import annotations

import json

import pytest

from runner.core.live_provider import LiveAgentProvider, LiveProviderError, LiveProviderSettings


def test_live_provider_is_stateless_and_preserves_missing_usage() -> None:
    captured: list[dict[str, object]] = []

    def transport(url: str, body: bytes, headers, timeout: float):
        del url, headers, timeout
        captured.append(json.loads(body))
        response = {
            "id": "resp-1",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {"name": "db.execute_readonly", "arguments": '{"sql":"select 1"}'},
                            }
                        ],
                    }
                }
            ],
        }
        return 200, json.dumps(response).encode()

    provider = LiveAgentProvider(
        LiveProviderSettings(provider="test", model="m", endpoint="https://example.invalid/v1/chat"),
        transport=transport,
    )
    turn = provider.complete(
        [{"role": "user", "content": "q"}],
        [{"name": "db.execute_readonly", "input_schema": {"type": "object"}}],
        {"temperature": 0, "max_output_tokens": 123, "seed": 7, "parallel_tool_calls": False},
        5,
    )

    assert provider.provider_kind == "live"
    assert provider.ranking_eligible is True
    assert turn.tool_calls[0].name == "db.execute_readonly"
    assert turn.tool_calls[0].arguments == {"sql": "select 1"}
    assert turn.usage.input_tokens is None
    assert turn.usage.output_tokens is None
    assert turn.usage.cached_input_tokens is None
    assert captured[0]["model"] == "m"
    assert captured[0]["temperature"] == 0
    assert captured[0]["max_tokens"] == 123
    assert captured[0]["seed"] == 7
    assert not hasattr(provider, "messages")


def test_credentialed_remote_endpoint_requires_https() -> None:
    with pytest.raises(LiveProviderError, match="must use HTTPS"):
        LiveAgentProvider(
            LiveProviderSettings(
                provider="test",
                model="m",
                endpoint="http://provider.example/v1/chat",
                api_key="secret",
            )
        )

    provider = LiveAgentProvider(
        LiveProviderSettings(
            provider="test",
            model="m",
            endpoint="http://127.0.0.1:8000/v1/chat",
            api_key="local-secret",
        ),
        transport=lambda *args: (200, b'{"choices":[{"message":{"content":"ok"}}]}'),
    )
    assert provider.settings.endpoint.startswith("http://127.0.0.1")


def test_live_provider_counts_retry_without_logging_reasoning() -> None:
    calls = 0

    def transport(url: str, body: bytes, headers, timeout: float):
        nonlocal calls
        del url, body, headers, timeout
        calls += 1
        if calls == 1:
            return 503, b"{}"
        return 200, json.dumps(
            {
                "id": "resp-2",
                "choices": [{"message": {"role": "assistant", "content": "done"}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 4, "prompt_tokens_details": {"cached_tokens": 2}},
            }
        ).encode()

    provider = LiveAgentProvider(
        LiveProviderSettings(
            provider="test",
            model="m",
            endpoint="https://example.invalid/v1/chat",
            max_retries=1,
            retry_backoff_seconds=0,
        ),
        transport=transport,
        sleep=lambda _: None,
    )
    turn = provider.complete([{"role": "user", "content": "q"}], [], {}, 5)

    assert provider.retry_count == 1
    assert provider.request_count == 2
    assert turn.usage.input_tokens == 11
    assert turn.usage.output_tokens == 4
    assert turn.usage.cached_input_tokens == 2
    assert "reasoning" not in repr(turn).lower()
