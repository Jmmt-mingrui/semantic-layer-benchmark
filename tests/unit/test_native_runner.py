from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from runner.core.agent import AgentTurn, ScriptedAgentProvider, ToolCall
from runner.core.native_adapter import NativeResponse
from runner.core.native_factory import NativeAdapterFactory, NativeFactorySettings, SUPPORTED_TARGETS
from runner.core.native_runner import NativeRunnerSettings, run_native_matrix, run_native_trial


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = yaml.safe_load((ROOT / "runner/config/targets.native.yaml").read_text(encoding="utf-8"))
TOOL_CATALOG = json.loads((ROOT / "runner/tools/blank-context.tools.json").read_text(encoding="utf-8"))


class NoQueryDatabase:
    settings = SimpleNamespace(schema="main")

    def execute(self, sql, parameters=None):  # pragma: no cover - scripted lifecycle never executes SQL
        raise AssertionError(f"unexpected database execution: {sql} {parameters}")


class FakeNativeAdapter:
    version = "fake-native-v1"

    def __init__(self, config):
        self.config = config
        self.closed = False

    def preflight(self, deadline_seconds):
        assert deadline_seconds > 0
        return (NativeResponse("ok", 0.0, {"native_operation": "fake.preflight"}),)

    def public_tools(self):
        return ()

    def dispatch(self, request):  # pragma: no cover
        raise AssertionError(request)

    def close(self):
        self.closed = True


def _factory(tmp_path: Path) -> NativeAdapterFactory:
    runtime = tmp_path / "mf"
    runtime.mkdir()
    overrides = {
        name: (lambda config, root, settings: FakeNativeAdapter(config))
        for name in ("metricflow", "ossie", "okf", "skill")
    }
    return NativeAdapterFactory(
        root=ROOT,
        registry=REGISTRY,
        database=NoQueryDatabase(),
        tool_catalog=TOOL_CATALOG,
        settings=NativeFactorySettings(
            metricflow_runtime_project_dir=runtime,
            skill_host_revision="test-host",
        ),
        adapter_overrides=overrides,
    )


def _settings() -> NativeRunnerSettings:
    return NativeRunnerSettings(
        provider_name="scripted-ci",
        model="scripted",
        temperature=0,
        max_output_tokens=100,
        max_turns=2,
        provider_timeout_seconds=3,
        tool_timeout_seconds=3,
    )


def _question() -> dict[str, object]:
    return {
        "question_id": "q01",
        "instance_id": "sf1-q01-test",
        "target_input": {"question": "Return the requested benchmark value."},
    }


def _unsupported_provider() -> ScriptedAgentProvider:
    return ScriptedAgentProvider(
        [
            AgentTurn(
                tool_calls=(
                    ToolCall(
                        id="submit-1",
                        name="benchmark.submit_result",
                        arguments={"status": "unsupported", "reason": "protocol lifecycle test"},
                    ),
                )
            )
        ]
    )


def test_all_six_targets_share_one_lifecycle_and_scripted_is_not_ranked(tmp_path: Path) -> None:
    providers: list[ScriptedAgentProvider] = []

    def provider_factory(target, repetition, context):
        del target, repetition, context
        provider = _unsupported_provider()
        providers.append(provider)
        return provider

    outcomes = run_native_matrix(
        targets=SUPPORTED_TARGETS,
        questions=[_question()],
        repetitions=2,
        adapter_factory=_factory(tmp_path),
        provider_factory=provider_factory,
        settings=_settings(),
        system_prompt="isolated system prompt",
    )

    assert len(outcomes) == 12
    assert len({id(provider) for provider in providers}) == 12
    assert all(item.record["conversation"]["fresh"] is True for item in outcomes)
    assert all(item.record["conversation"]["provider_closed_before_evaluation"] is True for item in outcomes)
    assert all(item.record["provider"]["ranking_eligible"] is False for item in outcomes)
    assert all(item.record["provider"]["kind"] == "scripted" for item in outcomes)
    assert all(item.record["usage"]["input_tokens"] == "unavailable" for item in outcomes)
    assert all(item.record["usage"]["output_tokens"] == "unavailable" for item in outcomes)
    assert all(item.record["status"] == "unsupported" for item in outcomes)

    for provider in providers:
        assert len(provider.calls) == 1
        first_messages = provider.calls[0][0]
        assert sum(message.get("role") == "user" for message in first_messages) == 1
        assert not any("previous" in str(message.get("content", "")).lower() for message in first_messages)


def test_gold_and_tool_overreach_fail_closed(tmp_path: Path) -> None:
    factory = _factory(tmp_path)

    def gold_provider(target, repetition, context):
        del target, repetition, context
        return ScriptedAgentProvider(
            [AgentTurn(tool_calls=(ToolCall("gold", "benchmark.read_gold", {},),))]
        )

    gold = run_native_trial(
        target="ossie",
        question_instance=_question(),
        repetition=1,
        adapter_factory=factory,
        provider_factory=gold_provider,
        settings=_settings(),
        system_prompt="isolated",
    )
    assert gold.record["status"] == "invalid"
    assert gold.record["error"]["category"] == "protocol_violation"
    assert "gold" in (gold.record["error"]["detail"] or "").lower()

    def sql_provider(target, repetition, context):
        del target, repetition, context
        return ScriptedAgentProvider(
            [AgentTurn(tool_calls=(ToolCall("sql", "db.execute_readonly", {"sql": "select 1"}),))]
        )

    metricflow = run_native_trial(
        target="metricflow",
        question_instance=_question(),
        repetition=1,
        adapter_factory=factory,
        provider_factory=sql_provider,
        settings=_settings(),
        system_prompt="isolated",
    )
    assert metricflow.record["status"] == "invalid"
    assert metricflow.record["error"]["category"] == "protocol_violation"
    assert metricflow.record["native_execution"]["fallback_used"] is False
