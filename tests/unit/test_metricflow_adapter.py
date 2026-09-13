from __future__ import annotations

from pathlib import Path

import pytest

from runner.adapters.metricflow import (
    METRICFLOW_CLI_VERSION,
    CommandResult,
    MetricFlowAdapter,
    MetricFlowConfigurationError,
    MetricFlowPreflightError,
)
from runner.core.native_adapter import NativeIsolationError, NativeOperationError, NativeRequest


class FakeSubprocessBoundary:
    """Records CLI argv without starting a MetricFlow process."""

    def __init__(self, responses: dict[tuple[str, ...], CommandResult] | None = None) -> None:
        self.calls: list[tuple[tuple[str, ...], Path, float]] = []
        self.responses = responses or {}

    def __call__(self, argv: list[str], cwd: Path, deadline_seconds: float) -> CommandResult:
        key = tuple(argv)
        self.calls.append((key, cwd, deadline_seconds))
        return self.responses.get(key, CommandResult(returncode=0, stdout="ok"))


def _target_config() -> dict[str, object]:
    return {
        "role": "executable_semantic_engine",
        "native_surface": {
            "name": "self_hosted_metricflow_cli",
            "artifact_root": "semantic-models/metricflow/tpcds-sf1",
        },
        "allowed_operations": [
            "metricflow.list_metrics",
            "metricflow.list_dimensions",
            "metricflow.list_dimension_values",
            "metricflow.list_entities",
            "metricflow.query",
            "benchmark.submit_result",
        ],
        "prohibited_operations": ["db.execute_readonly", "benchmark.read_gold"],
    }


def _adapter(tmp_path: Path, runner: FakeSubprocessBoundary | None = None) -> tuple[MetricFlowAdapter, FakeSubprocessBoundary]:
    model_root = tmp_path / "semantic-models"
    (model_root / "semantic_models").mkdir(parents=True)
    (model_root / "project_configuration.yml").write_text("version: 0.1\n", encoding="utf-8")
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    (runtime_root / "dbt_project.yml").write_text("name: benchmark\n", encoding="utf-8")
    boundary = runner or FakeSubprocessBoundary(
        {("mf", "--version"): CommandResult(returncode=0, stdout=f"mf, version {METRICFLOW_CLI_VERSION}\n")}
    )
    return (
        MetricFlowAdapter(
            target_config=_target_config(),
            model_root=model_root,
            runtime_project_dir=runtime_root,
            command_runner=boundary,
        ),
        boundary,
    )


def test_preflight_uses_pinned_cli_commands_and_validates_layout(tmp_path: Path) -> None:
    adapter, boundary = _adapter(tmp_path)

    responses = adapter.preflight(30)

    assert [response.status for response in responses] == ["succeeded"] * 4
    assert [call[0] for call in boundary.calls] == [
        ("mf", "--version"),
        ("mf", "health-checks"),
        ("mf", "validate-configs"),
    ]
    assert all(call[1] == tmp_path / "runtime" for call in boundary.calls)
    assert responses[0].request_artifact.startswith("sha256:")
    assert responses[-1].response_artifact.startswith("sha256:")


def test_dispatch_preserves_native_cli_payloads_after_preflight(tmp_path: Path) -> None:
    adapter, boundary = _adapter(tmp_path)
    adapter.preflight(30)

    metrics = adapter.dispatch(NativeRequest("metricflow.list_metrics", {}, 5))
    dimensions = adapter.dispatch(NativeRequest("metricflow.list_dimensions", {"metrics": ["orders", "revenue"]}, 5))
    values = adapter.dispatch(
        NativeRequest(
            "metricflow.list_dimension_values",
            {"metrics": ["orders"], "dimension": "customer__country", "start_time": "2024-01-01", "end_time": "2024-02-01"},
            5,
        )
    )
    query = adapter.dispatch(
        NativeRequest(
            "metricflow.query",
            {
                "metrics": ["orders"],
                "group_by": ["metric_time__month"],
                "where": ["{{ Dimension('customer__country') }} = 'US'"],
                "order": ["-orders"],
                "limit": 10,
            },
            5,
        )
    )

    assert [call[0] for call in boundary.calls[3:]] == [
        ("mf", "list", "metrics"),
        ("mf", "list", "dimensions", "--metrics", "orders,revenue"),
        (
            "mf",
            "list",
            "dimension-values",
            "--metrics",
            "orders",
            "--dimension",
            "customer__country",
            "--start-time",
            "2024-01-01",
            "--end-time",
            "2024-02-01",
        ),
        (
            "mf",
            "query",
            "--metrics",
            "orders",
            "--group-by",
            "metric_time__month",
            "--order",
            "-orders",
            "--where",
            "{{ Dimension('customer__country') }} = 'US'",
            "--limit",
            "10",
        ),
    ]
    assert metrics.output["native_operation"] == "metricflow.list_metrics"
    assert dimensions.status == values.status == query.status == "succeeded"
    assert "sql" not in " ".join(query.output["argv"]).lower()


def test_adapter_is_fail_closed_and_rejects_sql_fallback(tmp_path: Path) -> None:
    adapter, boundary = _adapter(tmp_path)

    with pytest.raises(MetricFlowPreflightError):
        adapter.dispatch(NativeRequest("metricflow.query", {"metrics": ["orders"]}, 5))
    assert boundary.calls == []

    adapter.preflight(30)
    with pytest.raises(NativeIsolationError):
        adapter.dispatch(NativeRequest("db.execute_readonly", {"sql": "select 1"}, 5))
    with pytest.raises(NativeOperationError):
        adapter.dispatch(NativeRequest("metricflow.explain", {}, 5))


def test_version_mismatch_stops_before_health_checks(tmp_path: Path) -> None:
    boundary = FakeSubprocessBoundary({("mf", "--version"): CommandResult(returncode=0, stdout="mf, version 0.999.0\n")})
    adapter, boundary = _adapter(tmp_path, boundary)

    responses = adapter.preflight(30)

    assert [response.status for response in responses] == ["succeeded", "failed"]
    assert [call[0] for call in boundary.calls] == [("mf", "--version")]
    with pytest.raises(MetricFlowPreflightError):
        adapter.dispatch(NativeRequest("metricflow.list_metrics", {}, 5))


def test_semantic_cli_rejection_is_recorded_as_unsupported_without_fallback(tmp_path: Path) -> None:
    boundary = FakeSubprocessBoundary(
        {
            ("mf", "--version"): CommandResult(returncode=0, stdout=f"mf, version {METRICFLOW_CLI_VERSION}\n"),
            ("mf", "query", "--metrics", "unknown_metric"): CommandResult(
                returncode=1, stderr="Metric unknown_metric not found"
            ),
        }
    )
    adapter, boundary = _adapter(tmp_path, boundary)
    adapter.preflight(30)

    response = adapter.dispatch(NativeRequest("metricflow.query", {"metrics": ["unknown_metric"]}, 5))

    assert response.status == "unsupported"
    assert len(boundary.calls) == 4
    assert all("select" not in " ".join(call[0]).lower() for call in boundary.calls)


def test_unknown_arguments_are_not_silently_forwarded(tmp_path: Path) -> None:
    adapter, _ = _adapter(tmp_path)
    adapter.preflight(30)

    with pytest.raises(MetricFlowConfigurationError, match="Unsupported"):
        adapter.dispatch(NativeRequest("metricflow.query", {"metrics": ["orders"], "sql": "select 1"}, 5))


def test_public_tools_are_native_only(tmp_path: Path) -> None:
    adapter, _ = _adapter(tmp_path)

    assert [tool["name"] for tool in adapter.public_tools()] == [
        "metricflow.list_metrics",
        "metricflow.list_dimensions",
        "metricflow.list_dimension_values",
        "metricflow.list_entities",
        "metricflow.query",
    ]
