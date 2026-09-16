from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.core.publication_orchestrator import (
    PublicationOrchestrationError,
    build_publication_manifest,
    materialize_publication_trial,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "runner/contracts"


def _candidate(result_hash: str = "a" * 64):
    return {
        "schema_version": "0.2.0",
        "trial_id": "q01-ossie-r01",
        "question": {"question_id": "q01", "instance_id": "q01-instance", "question_sha256": "1" * 64},
        "condition": {
            "target": "ossie", "repetition": 1, "native_surface": "ossie_yaml_spec_consumer",
            "artifact_sha256": "2" * 64, "adapter_version": "ossie-v1",
        },
        "conversation": {
            "fresh": True, "provider_closed_before_evaluation": True,
            "system_prompt_sha256": "3" * 64, "tool_schema_sha256": "4" * 64,
            "message_manifest": [{"role": "system", "content_sha256": "5" * 64}, {"role": "user", "content_sha256": "6" * 64}],
            "message_count": 2, "provider_response_ids": ["response-1"],
        },
        "provider": {"kind": "live", "ranking_eligible": True},
        "native_execution": {"used_only_declared_surface": True, "requests": [], "fallback_used": False},
        "candidate": {
            "sql_artifacts": [{"result_handle": "r1", "sql_sha256": "7" * 64}],
            "result_artifacts": [{"result_handle": "r1", "result_sha256": result_hash}],
        },
        "usage": {"input_tokens": "unavailable", "output_tokens": 9, "cached_input_tokens": None, "reasoning_tokens": 4, "tool_calls": 2, "database_calls": 1, "total_latency_ms": 10.0},
        "error": {"category": None, "detail": None},
        "status": "candidate_ready",
    }


def _gold(result_hash: str = "a" * 64):
    return {
        "question_id": "q01", "instance_id": "q01-instance",
        "statements": [{"result": {"sha256": result_hash}}],
    }


def _trace():
    return (
        {"sequence": 0, "event_type": "trial.start", "status": "started", "attributes": {}},
        {"sequence": 1, "event_type": "llm.generate", "status": "ok", "attributes": {},
         "usage": {"input_tokens": 10, "output_tokens": 9, "cached_input_tokens": 0,
                   "reasoning_tokens": 4, "provider_reported": True}},
        {"sequence": 2, "event_type": "conversation.close", "status": "ok", "attributes": {"provider_closed": True}},
        {"sequence": 3, "event_type": "trial.finish", "status": "ok", "attributes": {}},
    )


def test_materializes_schema_valid_trial_only_after_close(tmp_path: Path) -> None:
    record = materialize_publication_trial(
        run_id="run-1", experiment_id="representative-v1", lane="native_end_to_end",
        candidate=_candidate(), native_trace=_trace(), gold=_gold(), output_dir=tmp_path,
        contracts_dir=CONTRACTS, timestamp="2026-09-14T00:00:00Z",
    )
    assert record["status"] == "passed"
    assert record["evaluation"]["result_equivalent"] is True
    assert record["conversation"]["provider_conversation_id"].startswith("conv-")
    assert record["usage"]["input_tokens"] is None
    assert record["usage"]["reasoning_tokens"] == 4
    trial_dir = tmp_path / "trials/q01-ossie-r01"
    assert (trial_dir / "trial.json").is_file()
    assert (trial_dir / "trace.jsonl").is_file()
    trace = [json.loads(line) for line in (trial_dir / "trace.jsonl").read_text().splitlines()]
    assert trace[1]["usage"]["reasoning_tokens"] == 4
    assert (trial_dir / "conversation.sanitized.jsonl").is_file()


def test_refuses_gold_evaluation_before_provider_close(tmp_path: Path) -> None:
    candidate = _candidate()
    candidate["conversation"]["provider_closed_before_evaluation"] = False
    with pytest.raises(PublicationOrchestrationError, match="closed"):
        materialize_publication_trial(
            run_id="run-1", experiment_id="representative-v1", lane="native_end_to_end",
            candidate=candidate, native_trace=_trace(), gold=_gold(), output_dir=tmp_path,
            contracts_dir=CONTRACTS,
        )


def test_wrong_result_is_a_failed_trial(tmp_path: Path) -> None:
    record = materialize_publication_trial(
        run_id="run-1", experiment_id="representative-v1", lane="native_end_to_end",
        candidate=_candidate("b" * 64), native_trace=_trace(), gold=_gold(), output_dir=tmp_path,
        contracts_dir=CONTRACTS,
    )
    assert record["status"] == "failed"
    assert record["evaluation"]["error_category"] == "wrong_result"


def test_publication_manifest_requires_the_complete_matrix(tmp_path: Path) -> None:
    pack = tmp_path / "pack.json"
    pack.write_text("{}", encoding="utf-8")
    targets = ("blank_context", "ddl_only", "metricflow", "ossie", "okf", "skill")
    questions = ("q01", "q02", "q03", "q05", "q12", "q14", "q21", "q36", "q39", "q49", "q75", "q84")
    trials = []
    for question in questions:
        for target in targets:
            for repetition in (1, 2, 3):
                trials.append({
                    "condition": {"target": target, "repetition": repetition},
                    "conversation": {"tool_schema_sha256": (targets.index(target) + 1).__format__("064x")},
                    "question": {"question_id": question},
                    "evaluation": {"reference_result_sha256": (questions.index(question) + 100).__format__("064x")},
                })
    manifest = build_publication_manifest(
        run_id="run-1", experiment_id="representative-v1", dataset_manifest_sha256="d" * 64,
        gold_pack_path=pack, provider="provider", model="model", trials=trials,
        contracts_dir=CONTRACTS, finished_at="2026-09-14T00:00:00Z",
    )
    assert manifest["trial_count"] == 216
    assert set(manifest["tool_schema_sha256_by_target"]) == set(targets)
