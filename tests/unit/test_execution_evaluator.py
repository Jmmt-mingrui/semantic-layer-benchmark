from __future__ import annotations

import pytest

from evaluators.execution import (
    EXPECTED_TRIALS,
    QUESTION_IDS,
    TARGETS,
    ExecutionEvaluationError,
    evaluate_execution,
)


TOOL_SHA = {target: f"{index + 1:064x}" for index, target in enumerate(TARGETS)}
GOLD_SHA = {question: f"{index + 100:064x}" for index, question in enumerate(QUESTION_IDS)}


def _manifest():
    return {
        "run_id": "run-publication-001",
        "experiment_id": "representative-v1",
        "status": "completed",
        "finished_at": "2026-09-14T00:00:00Z",
        "dataset_manifest_sha256": "a" * 64,
        "gold_pack_sha256": "b" * 64,
        "provider": "test-provider",
        "model": "test-model",
        "tool_schema_sha256_by_target": TOOL_SHA,
        "gold_result_sha256_by_question": GOLD_SHA,
    }


def _records():
    rows = []
    sequence = 0
    for question in QUESTION_IDS:
        for target_index, target in enumerate(TARGETS):
            for repetition in (1, 2, 3):
                sequence += 1
                correct = target_index % 2 == 0
                rows.append(
                    {
                        "run_id": "run-publication-001",
                        "trial_id": f"trial-{sequence:03d}",
                        "experiment_id": "representative-v1",
                        "question": {"question_id": question},
                        "condition": {"target": target, "repetition": repetition},
                        "conversation": {
                            "fresh": True,
                            "provider_conversation_id": f"conversation-{sequence:03d}",
                            "provider_response_ids": [f"response-{sequence:03d}"],
                            "tool_schema_sha256": TOOL_SHA[target],
                        },
                        "native_execution": {"used_only_declared_surface": True, "fallback_used": False},
                        "candidate": {"statement_count": 1},
                        "evaluation": {
                            "execution_success": True,
                            "result_equivalent": correct,
                            "reference_result_sha256": GOLD_SHA[question],
                            "error_category": None if correct else "wrong_result",
                        },
                        "usage": {
                            "input_tokens": None if repetition == 3 else 100,
                            "output_tokens": 10,
                            "cached_input_tokens": None,
                            "tool_calls": 2,
                            "database_calls": 1,
                            "total_latency_ms": float(100 + repetition),
                        },
                        "status": "passed" if correct else "failed",
                    }
                )
    return rows


def _evaluate(rows):
    return evaluate_execution(rows, publication=True, run_manifest=_manifest())


def test_publication_matrix_and_unavailable_tokens() -> None:
    rows = _records()
    assert len(rows) == EXPECTED_TRIALS == 216
    report = _evaluate(rows)
    assert report["trial_count"] == 216
    assert report["question_denominator"] == 12
    assert report["global_winner"] is None
    blank = report["targets"]["blank_context"]
    assert blank["execution_accuracy"] == 1.0
    assert blank["tokens"]["input_tokens"]["unavailable_trials"] == 12
    assert blank["tokens"]["input_tokens"]["total"] is None
    assert blank["tokens"]["input_tokens"]["known_total"] == 2400
    assert blank["tokens"]["cached_input_tokens"]["total"] is None
    assert blank["tokens"]["reasoning_tokens"]["unavailable_trials"] == 36
    assert blank["three_run_consistency"] == 1.0


def test_publication_requires_run_manifest() -> None:
    with pytest.raises(ExecutionEvaluationError, match="run manifest"):
        evaluate_execution(_records(), publication=True)


def test_publication_fails_closed_on_missing_trial() -> None:
    rows = _records()
    rows.pop()
    with pytest.raises(ExecutionEvaluationError, match="exactly 216"):
        _evaluate(rows)


def test_publication_fails_closed_on_context_reuse() -> None:
    rows = _records()
    rows[0]["conversation"]["fresh"] = False
    with pytest.raises(ExecutionEvaluationError, match="Fresh-context"):
        _evaluate(rows)


def test_publication_fails_closed_on_duplicate_conversation_identity() -> None:
    rows = _records()
    rows[1]["conversation"]["provider_conversation_id"] = rows[0]["conversation"]["provider_conversation_id"]
    with pytest.raises(ExecutionEvaluationError, match="Unique conversation identity"):
        _evaluate(rows)


def test_publication_fails_closed_on_open_lifecycle() -> None:
    rows = _records()
    rows[0]["conversation"]["provider_response_ids"] = []
    with pytest.raises(ExecutionEvaluationError, match="lifecycle closure"):
        _evaluate(rows)


def test_publication_fails_closed_on_tool_schema_mismatch() -> None:
    rows = _records()
    rows[0]["conversation"]["tool_schema_sha256"] = "f" * 64
    with pytest.raises(ExecutionEvaluationError, match="Tool-schema identity"):
        _evaluate(rows)


def test_publication_fails_closed_on_gold_mismatch() -> None:
    rows = _records()
    rows[0]["evaluation"]["reference_result_sha256"] = "f" * 64
    with pytest.raises(ExecutionEvaluationError, match="Frozen Gold binding"):
        _evaluate(rows)


def test_multi_formulation_questions_keep_one_question_denominator() -> None:
    report = _evaluate(_records())
    assert report["question_denominator"] == 12
    for comparison in report["paired_comparisons"].values():
        assert comparison["question_pairs"] == 12
        assert comparison["unit_of_analysis"] == "question"
        assert comparison["paired_95pct_ci_method"].startswith("paired percentile bootstrap")
        assert comparison["bootstrap_samples"] == 20_000
