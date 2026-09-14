from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from runner.adapters.metricflow import CommandResult
from runner.adapters.metricflow_result import MetricFlowResultAdapter
from runner.core.native_adapter import NativeRequest
from runner.core.native_factory import NativeAdapterFactory, NativeFactorySettings


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = yaml.safe_load((ROOT / "runner/config/targets.native.yaml").read_text(encoding="utf-8"))
TOOLS = json.loads((ROOT / "runner/tools/blank-context.tools.json").read_text(encoding="utf-8"))


class NoQueryDatabase:
    settings = SimpleNamespace(schema="main")

    def execute(self, sql, parameters=None):  # pragma: no cover
        raise AssertionError(f"MetricFlow must not fall back to database SQL: {sql} {parameters}")


def test_metricflow_query_registers_native_result_handle_without_sql_fallback(tmp_path: Path) -> None:
    model_root = tmp_path / "model"
    (model_root / "semantic_models").mkdir(parents=True)
    (model_root / "project_configuration.yml").write_text("project_configuration: {}\n", encoding="utf-8")
    runtime_project = tmp_path / "runtime"
    runtime_project.mkdir()
    (runtime_project / "dbt_project.yml").write_text("name: fixture\n", encoding="utf-8")

    def command_runner(argv, cwd, timeout_seconds):
        del cwd, timeout_seconds
        if argv[1:] == ["--version"]:
            return CommandResult(0, "0.213.0.dev0\n", "")
        if argv[1:] in (["health-checks"], ["validate-configs"]):
            return CommandResult(0, "ok\n", "")
        if argv[1] == "query":
            csv_path = Path(argv[argv.index("--csv") + 1])
            csv_path.write_text("metric_time,revenue,count\n2001-01-01,12.50,3\n", encoding="utf-8")
            return CommandResult(0, "", "")
        raise AssertionError(argv)

    def override(config, artifact_root, settings):
        return MetricFlowResultAdapter(
            target_config=config,
            model_root=model_root,
            runtime_project_dir=runtime_project,
            executable="mf",
            command_runner=command_runner,
        )

    factory = NativeAdapterFactory(
        root=ROOT,
        registry=REGISTRY,
        database=NoQueryDatabase(),
        tool_catalog=TOOLS,
        settings=NativeFactorySettings(metricflow_runtime_project_dir=runtime_project),
        adapter_overrides={"metricflow": override},
    )
    native = factory.create("metricflow")
    assert all(response.status == "succeeded" for response in native.preflight(5))
    response = native.dispatch(
        NativeRequest(operation="metricflow.query", arguments={"metrics": ["revenue"]}, deadline_seconds=5)
    )
    assert response.status == "succeeded"
    assert response.output["result_source"] == "metricflow_native_cli"
    assert response.output["result_handle"] == "result-001"
    assert response.output["columns"] == ["metric_time", "revenue", "count"]
    assert response.output["row_count"] == 1
    assert response.output["preview_rows"] == [["2001-01-01", "12.50", 3]]

    submitted = native.dispatch(
        NativeRequest(
            operation="benchmark.submit_result",
            arguments={"status": "success", "result_handles": ["result-001"]},
            deadline_seconds=5,
        )
    )
    assert submitted.output == {"accepted": True}
    assert native.database_calls == 0
    assert native.sql_by_handle == {}
    native.close()
