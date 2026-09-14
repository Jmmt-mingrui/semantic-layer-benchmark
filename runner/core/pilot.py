"""Executable 18-trial representative pilot orchestration.

The pilot proves the complete native lifecycle with q01, six targets, and three
fresh repetitions. Its manifest is explicitly non-publishable; publication
still requires the frozen 12 x 6 x 3 matrix.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
import yaml

from runner.adapters.metricflow_result import MetricFlowResultAdapter
from runner.core.database import connect, load_database_settings
from runner.core.live_provider import LiveAgentProvider, LiveProviderSettings
from runner.core.native_factory import NativeAdapterFactory, NativeFactorySettings, SUPPORTED_TARGETS
from runner.core.native_runner import NativeRunnerSettings, run_native_matrix
from runner.core.publication_orchestrator import load_gold_for_candidate, materialize_publication_trial


PILOT_QUESTION_ID = "q01"
PILOT_REPETITIONS = 3
PILOT_TRIALS = len(SUPPORTED_TARGETS) * PILOT_REPETITIONS


class PilotConfigurationError(RuntimeError):
    pass


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise PilotConfigurationError(f"Required environment variable is missing: {name}")
    return value


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load_q01(path: Path) -> dict[str, Any]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    matches = [row for row in rows if row.get("question_id") == PILOT_QUESTION_ID]
    if len(matches) != 1:
        raise PilotConfigurationError("Representative instances must resolve q01 exactly once")
    return matches[0]


def _provider_settings() -> LiveProviderSettings:
    key_env = os.getenv("BENCHMARK_AGENT_API_KEY_ENV")
    if key_env and not os.getenv(key_env):
        raise PilotConfigurationError(f"Provider credential variable is missing: {key_env}")
    return LiveProviderSettings(
        provider=_required_env("BENCHMARK_AGENT_PROVIDER"),
        model=_required_env("BENCHMARK_AGENT_MODEL"),
        endpoint=_required_env("BENCHMARK_AGENT_ENDPOINT"),
        api_key_env=key_env,
        max_retries=int(os.getenv("BENCHMARK_AGENT_MAX_RETRIES", "2")),
    )


def _validate_manifest(manifest: Mapping[str, Any], schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(manifest),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise PilotConfigurationError(f"Pilot manifest is invalid: {errors[0].message}")


def run_representative_pilot(
    *,
    root: str | Path,
    output_dir: str | Path,
    database_config: str | Path = "runner/config/database.yaml",
    instances_path: str | Path = "benchmark/tpcds/questions/instances/sf1-representative-v1.jsonl",
    gold_pack_path: str | Path = "benchmark/tpcds/results/gold/sf1/representative-v1/pack.json",
    metricflow_runtime_project_dir: str | Path,
    metricflow_executable: str = "mf",
    skill_host_revision: str | None = None,
) -> Path:
    """Run the fixed q01 x six targets x three repetitions pilot."""

    root_path = Path(root).resolve()
    output = Path(output_dir)
    if not output.is_absolute():
        output = root_path / output
    if output.exists():
        raise PilotConfigurationError(f"Pilot output already exists: {output}")

    def within(value: str | Path, label: str) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = root_path / path
        resolved = path.resolve()
        if not resolved.is_relative_to(root_path):
            raise PilotConfigurationError(f"{label} must remain inside the repository root")
        return resolved

    database_path = within(database_config, "Database config")
    instances = within(instances_path, "Question instances")
    pack_path = within(gold_pack_path, "Gold pack")
    mf_runtime = within(metricflow_runtime_project_dir, "MetricFlow runtime project")
    contracts = root_path / "runner/contracts"
    registry_path = root_path / "runner/config/targets.native.yaml"
    tools_path = root_path / "runner/tools/blank-context.tools.json"
    system_prompt_path = root_path / "runner/prompts/native-agent-system.md"
    required_files = (database_path, instances, pack_path, registry_path, tools_path, system_prompt_path)
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing or not mf_runtime.is_dir():
        raise PilotConfigurationError(f"Pilot inputs are missing: {missing or [str(mf_runtime)]}")

    provider_settings = _provider_settings()
    revision = skill_host_revision or _required_env("BENCHMARK_SKILL_HOST_REVISION")
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    tool_catalog = json.loads(tools_path.read_text(encoding="utf-8"))
    question = _load_q01(instances)
    gold_entry = next((entry for entry in json.loads(pack_path.read_text())["gold"] if entry["question_id"] == "q01"), None)
    if gold_entry is None:
        raise PilotConfigurationError("Frozen Gold pack has no q01 entry")
    gold_path = root_path / gold_entry["path"]

    run_id = "pilot-q01-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True, exist_ok=False)
    settings = NativeRunnerSettings(
        provider_name=provider_settings.provider,
        model=provider_settings.model,
        temperature=0,
        max_output_tokens=4096,
        max_turns=12,
        provider_timeout_seconds=120,
        tool_timeout_seconds=60,
        seed=20260914,
        parallel_tool_calls=False,
    )

    def provider_factory(target: str, repetition: int, context: Mapping[str, str]) -> LiveAgentProvider:
        del target, repetition, context
        return LiveAgentProvider(provider_settings)

    def metricflow_factory(config: dict[str, Any], model_root: Path, factory_settings: NativeFactorySettings):
        return MetricFlowResultAdapter(
            target_config=config,
            model_root=model_root,
            runtime_project_dir=factory_settings.metricflow_runtime_project_dir,
            executable=factory_settings.metricflow_executable,
        )

    trials: list[dict[str, Any]] = []
    with connect(load_database_settings(database_path)) as database:
        factory = NativeAdapterFactory(
            root=root_path,
            registry=registry,
            database=database,
            tool_catalog=tool_catalog,
            settings=NativeFactorySettings(
                metricflow_runtime_project_dir=mf_runtime,
                metricflow_executable=metricflow_executable,
                skill_host_revision=revision,
            ),
            adapter_overrides={"metricflow": metricflow_factory},
        )
        outcomes = run_native_matrix(
            targets=SUPPORTED_TARGETS,
            questions=[question],
            repetitions=PILOT_REPETITIONS,
            adapter_factory=factory,
            provider_factory=provider_factory,
            settings=settings,
            system_prompt=system_prompt_path.read_text(encoding="utf-8"),
        )
        for outcome in outcomes:
            gold, _ = load_gold_for_candidate(
                outcome.record, gold_path=gold_path, gold_pack_path=pack_path, root=root_path
            )
            trials.append(materialize_publication_trial(
                run_id=run_id,
                experiment_id="representative-v1",
                lane="native_end_to_end",
                candidate=outcome.record,
                native_trace=outcome.trace,
                gold=gold,
                output_dir=output,
                contracts_dir=contracts,
            ))

    if len(trials) != PILOT_TRIALS:
        raise PilotConfigurationError(f"Pilot must produce exactly {PILOT_TRIALS} trials")
    manifest = {
        "schema_version": "0.1.0",
        "run_id": run_id,
        "experiment_id": "representative-v1",
        "mode": "pilot",
        "publishable": False,
        "question_ids": [PILOT_QUESTION_ID],
        "targets": list(SUPPORTED_TARGETS),
        "repetitions": PILOT_REPETITIONS,
        "trial_count": len(trials),
        "dataset_config_sha256": _sha(database_path),
        "gold_pack_sha256": _sha(pack_path),
        "provider": provider_settings.provider,
        "model": provider_settings.model,
        "finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    _validate_manifest(manifest, contracts / "pilot-run-manifest.schema.json")
    manifest_path = output / "pilot-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path
