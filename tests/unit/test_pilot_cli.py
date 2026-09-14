from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from runner.cli import build_parser
from runner.core.control_tools import ControlToolDispatcher
from runner.core.native_adapter import NativeRequest, NativeResponse
from runner.core.native_factory import NativeRuntime


class FakeDatabase:
    settings = SimpleNamespace(schema="main")


class NativeResultAdapter:
    version = "native-result-test"

    def dispatch(self, request):
        assert request.operation == "metricflow.query"
        return NativeResponse(
            status="succeeded",
            duration_ms=2.5,
            output={
                "native_result": {"columns": ["metric_time", "revenue"], "rows": [["2000-01-01", 42]]},
                "native_result_identity": {"row_count": 1},
            },
            response_artifact="sha256:" + "a" * 64,
        )

    def close(self):
        pass


def test_metricflow_native_result_becomes_submittable_without_sql_fallback() -> None:
    tools = {
        "tools": [
            {
                "name": "benchmark.submit_result",
                "description": "submit",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
            }
        ]
    }
    harness = ControlToolDispatcher(FakeDatabase(), tools, {"benchmark.submit_result"})
    runtime = NativeRuntime(
        target="metricflow",
        target_config={"allowed_operations": ["metricflow.query", "benchmark.submit_result"]},
        harness=harness,
        native_adapter=NativeResultAdapter(),
        initial_context=None,
        artifact_sha256="b" * 64,
    )
    response = runtime.dispatch(NativeRequest("metricflow.query", {}, 3))
    assert response.output["result_handle"] == "result-001"
    assert response.output["row_count"] == 1
    assert "native_result" not in response.output
    assert "result-001" in runtime.results
    assert runtime.sql_by_handle == {}
    assert runtime.database_calls == 0


def test_cli_exposes_explicit_non_publishable_pilot_command(tmp_path: Path) -> None:
    args = build_parser().parse_args(
        ["run-pilot", "--output", str(tmp_path / "run"), "--metricflow-runtime", str(tmp_path / "mf")]
    )
    assert args.command == "run-pilot"
    assert args.output == tmp_path / "run"
    assert args.metricflow_runtime == tmp_path / "mf"
