from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.generate_run_report import (
    ReportInputError,
    build_report,
    generate_report_files,
    render_markdown,
)


SHA = "a" * 64
REPOSITORY_SHA = "b" * 40


def _trial(run_id: str, trial_id: str, status: str, index: int) -> dict:
    error = {
        "passed": None,
        "failed": "wrong_result",
        "unsupported": "unsupported_semantics",
        "invalid": "agent_protocol",
    }[status]
    tokens = {
        "passed": (100, 20, 10),
        "failed": (None, None, None),
        "unsupported": (50, 5, 0),
        "invalid": (0, 0, 0),
    }[status]
    calls = {
        "passed": (3, 1, 2),
        "failed": (2, 1, 0),
        "unsupported": (1, 0, 1),
        "invalid": (0, 0, None),
    }[status]
    latency = {"passed": 100.0, "failed": 200.0, "unsupported": 50.0, "invalid": 25.0}[status]
    requests = []
    if calls[0]:
        requests.append(
            {"operation": "native.query", "status": "unsupported" if status == "unsupported" else "ok", "duration_ms": latency / 2}
        )
    trial = {
        "schema_version": "0.1.0",
        "run_id": run_id,
        "trial_id": trial_id,
        "experiment_id": "report-test",
        "question": {"question_id": f"q{index:02d}", "instance_id": f"instance-{index}", "target_prompt_sha256": SHA},
        "condition": {
            "target": "metricflow",
            "lane": "native_end_to_end",
            "repetition": 1,
            "native_surface": "metricflow-cli",
            "artifact_sha256": SHA,
            "adapter_version": "test-v1",
        },
        "conversation": {
            "fresh": True,
            "system_prompt_sha256": SHA,
            "tool_schema_sha256": SHA,
            "sanitized_transcript": "deliberately/unavailable/conversation.jsonl",
            "message_count": 2,
            "provider_conversation_id": None,
            "provider_response_ids": [],
        },
        "native_execution": {
            "used_only_declared_surface": True,
            "requests": requests,
            "fallback_used": False,
            "unsupported_reason": "not expressible" if status == "unsupported" else None,
        },
        "candidate": {
            "statement_count": 0 if status in {"unsupported", "invalid"} else 1,
            "sql_artifacts": ["deliberately/unavailable/candidate.sql"],
            "result_artifacts": ["deliberately/unavailable/candidate.result.json"],
            "answer_artifact": None,
        },
        "evaluation": {
            "execution_success": status in {"passed", "failed"},
            "result_equivalent": True if status == "passed" else False if status == "failed" else None,
            "reference_result_sha256": SHA if status in {"passed", "failed"} else None,
            "candidate_result_sha256": SHA if status in {"passed", "failed"} else None,
            "error_category": error,
        },
        "usage": {
            "input_tokens": tokens[0],
            "output_tokens": tokens[1],
            "cached_input_tokens": tokens[2],
            "tool_calls": calls[0],
            "database_calls": calls[1],
            "total_latency_ms": latency,
            "estimated_cost_usd": None,
            "price_snapshot": None,
        },
        "status": status,
    }
    if calls[2] is not None:
        trial["usage"]["native_service_calls"] = calls[2]
    return trial


def _trace(run_id: str, trial_id: str, duration: float) -> list[dict]:
    return [
        {
            "schema_version": "0.1.0",
            "run_id": run_id,
            "trial_id": trial_id,
            "sequence": 0,
            "timestamp": "2026-09-12T00:00:00Z",
            "event_type": "trial.start",
            "status": "started",
            "attributes": {},
        },
        {
            "schema_version": "0.1.0",
            "run_id": run_id,
            "trial_id": trial_id,
            "sequence": 1,
            "timestamp": "2026-09-12T00:00:01Z",
            "event_type": "trial.end",
            "status": "ok",
            "duration_ms": duration,
            "attributes": {},
        },
    ]


def _fixture(tmp_path: Path) -> Path:
    run_id = "run-report-test"
    run_directory = tmp_path / "runs" / run_id
    statuses = ("passed", "failed", "unsupported", "invalid")
    references = []
    for index, status in enumerate(statuses, start=1):
        trial_id = f"trial-{index}"
        trial_directory = run_directory / "trials" / trial_id
        trial_directory.mkdir(parents=True)
        trial_path = trial_directory / "trial.json"
        trial_path.write_text(json.dumps(_trial(run_id, trial_id, status, index)))
        trace = _trace(run_id, trial_id, float(index * 10))
        (trial_directory / "trace.jsonl").write_text("".join(json.dumps(event) + "\n" for event in trace))
        references.append(str(trial_path.relative_to(tmp_path)))
    run = {
        "schema_version": "0.1.0",
        "run_id": run_id,
        "experiment_id": "report-test",
        "started_at": "2026-09-12T00:00:00Z",
        "finished_at": "2026-09-12T00:01:00Z",
        "reproducibility": {
            "repository_sha": REPOSITORY_SHA,
            "experiment_sha256": SHA,
            "dataset_manifest_sha256": SHA,
            "target_registry_sha256": SHA,
        },
        "environment": {
            "os": "test",
            "architecture": "x86_64",
            "python": "3.12",
            "database": "duckdb 1.4.0",
            "cpu_limit": 1,
            "memory_limit_mb": 512,
        },
        "trial_records": references,
        "summary": {
            "planned": 4,
            "completed": 4,
            "passed": 1,
            "failed": 1,
            "unsupported": 1,
            "invalid": 1,
            "timeout": 0,
        },
        "status": "completed_with_failures",
    }
    run_path = run_directory / "run.json"
    run_path.write_text(json.dumps(run))
    return run_path


def test_report_aggregates_outcomes_usage_operations_and_latency(tmp_path: Path) -> None:
    run_path = _fixture(tmp_path)

    report = build_report(run_path.relative_to(tmp_path), artifact_root=tmp_path)

    assert report["validation"] == {
        "all_inputs_valid": True,
        "run_records": 1,
        "trial_records": 4,
        "trace_streams": 4,
        "trace_events": 8,
    }
    assert report["outcomes"]["by_status"] == {
        "passed": 1,
        "failed": 1,
        "unsupported": 1,
        "invalid": 1,
        "timeout": 0,
        "skipped": 0,
    }
    assert report["outcomes"]["correctness"] == {
        "evaluable_trials": 2,
        "passed": 1,
        "accuracy": 0.5,
    }
    assert report["outcomes"]["error_categories"] == {
        "agent_protocol": 1,
        "unsupported_semantics": 1,
        "wrong_result": 1,
    }
    assert report["usage"]["tokens"]["input_tokens"] == {
        "known_trials": 3,
        "unknown_trials": 1,
        "known_total": 150,
    }
    assert report["usage"]["calls"]["native_service_calls"] == {
        "known_trials": 3,
        "unknown_trials": 1,
        "known_total": 3,
    }
    assert report["latency_ms"]["trial_total"] == {
        "count": 4,
        "min": 25.0,
        "mean": 93.75,
        "p50": 75.0,
        "p95": 200.0,
        "max": 200.0,
    }
    assert report["native_operations"]["native.query"]["count"] == 3
    assert report["native_operations"]["native.query"]["by_status"] == {"ok": 2, "unsupported": 1}


def test_report_never_dereferences_secondary_artifacts(tmp_path: Path) -> None:
    run_path = _fixture(tmp_path)
    report = build_report(run_path.relative_to(tmp_path), artifact_root=tmp_path)
    assert report["validation"]["all_inputs_valid"] is True


def test_invalid_trace_fails_before_writing_output(tmp_path: Path) -> None:
    run_path = _fixture(tmp_path)
    trace_path = run_path.parent / "trials" / "trial-1" / "trace.jsonl"
    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    events[1]["sequence"] = 2
    trace_path.write_text("".join(json.dumps(event) + "\n" for event in events))
    output = tmp_path / "reports" / "run-report-test"

    with pytest.raises(ReportInputError, match="contiguous"):
        generate_report_files(run_path.relative_to(tmp_path), output, artifact_root=tmp_path)

    assert not output.exists()


def test_trial_reference_must_remain_inside_run_trials_directory(tmp_path: Path) -> None:
    run_path = _fixture(tmp_path)
    run = json.loads(run_path.read_text())
    run["trial_records"][0] = run["trial_records"][0].replace("runs/run-report-test/trials", "outside")
    run_path.write_text(json.dumps(run))
    outside = tmp_path / "outside" / "trial-1"
    outside.mkdir(parents=True)
    source = run_path.parent / "trials" / "trial-1"
    (outside / "trial.json").write_text((source / "trial.json").read_text())
    (outside / "trace.jsonl").write_text((source / "trace.jsonl").read_text())

    with pytest.raises(ReportInputError, match="artifact root"):
        build_report(run_path.relative_to(tmp_path), artifact_root=tmp_path)


def test_writes_deterministic_json_and_localized_markdown(tmp_path: Path) -> None:
    run_path = _fixture(tmp_path)
    output = tmp_path / "reports" / "run-report-test"
    json_path, markdown_path = generate_report_files(
        run_path.relative_to(tmp_path),
        output,
        artifact_root=tmp_path,
        language="zh-CN",
    )

    assert json.loads(json_path.read_text())["report_type"] == "offline_run_summary"
    assert markdown_path.read_text().startswith("# 离线 Benchmark 运行报告\n")
    assert "未知的 Provider 用量保持未知" in markdown_path.read_text()
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        generate_report_files(run_path.relative_to(tmp_path), output, artifact_root=tmp_path)


def test_english_is_the_default_markdown_language(tmp_path: Path) -> None:
    report = build_report(_fixture(tmp_path).relative_to(tmp_path), artifact_root=tmp_path)
    assert render_markdown(report).startswith("# Offline benchmark run report\n")
