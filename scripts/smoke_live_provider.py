"""Opt-in live provider smoke test.

This is deliberately not a benchmark run and never writes ranking artifacts.
It checks that a configured live provider can complete one fresh request through
the same provider boundary used by the native runner.
"""

from __future__ import annotations

from hashlib import sha256
import json
import os

from runner.core.live_provider import LiveAgentProvider, LiveProviderSettings


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> int:
    provider_name = _required("BENCHMARK_AGENT_PROVIDER")
    model = _required("BENCHMARK_AGENT_MODEL")
    endpoint = _required("BENCHMARK_AGENT_ENDPOINT")
    key_env = os.getenv("BENCHMARK_AGENT_API_KEY_ENV")
    settings = LiveProviderSettings(
        provider=provider_name,
        model=model,
        endpoint=endpoint,
        api_key_env=key_env,
        max_retries=int(os.getenv("BENCHMARK_AGENT_MAX_RETRIES", "2")),
        max_tokens_field=os.getenv("BENCHMARK_AGENT_MAX_TOKENS_FIELD", "max_tokens"),
    )
    provider = LiveAgentProvider(settings)
    turn = provider.complete(
        [
            {"role": "system", "content": "This is a non-publishing connectivity smoke test."},
            {"role": "user", "content": "Reply briefly with READY."},
        ],
        [],
        {
            "temperature": float(os.getenv("BENCHMARK_AGENT_TEMPERATURE", "0")),
            "max_output_tokens": int(os.getenv("BENCHMARK_AGENT_MAX_OUTPUT_TOKENS", "128")),
        },
        float(os.getenv("BENCHMARK_AGENT_TIMEOUT_SECONDS", "30")),
    )
    content = turn.content or ""
    output = {
        "smoke_only": True,
        "publishable_benchmark_result": False,
        "provider": provider_name,
        "model": model,
        "response_id": turn.response_id,
        "content_sha256": sha256(content.encode("utf-8")).hexdigest(),
        "input_tokens": turn.usage.input_tokens if turn.usage.input_tokens is not None else "unavailable",
        "output_tokens": turn.usage.output_tokens if turn.usage.output_tokens is not None else "unavailable",
        "cached_input_tokens": turn.usage.cached_input_tokens if turn.usage.cached_input_tokens is not None else "unavailable",
        "reasoning_tokens": turn.usage.reasoning_tokens if turn.usage.reasoning_tokens is not None else "unavailable",
        "usage_provider_reported": turn.usage.provider_reported,
        "retries": provider.retry_count,
    }
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
