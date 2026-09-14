from __future__ import annotations

import pytest

from evaluators.execution import (
    EXPECTED_TRIALS,
    QUESTION_IDS,
    TARGETS,
    ExecutionEvaluationError,
    evaluate_execution,
)


def _records():
    rows = []
    for question in QUESTION_IDS:
        for target_index, target in enumerate(TARGETS):
            for repetition in (1, 2, 3):
                correct = target_index % 2 == 0
                rows.append(
                    {
                        "question": {"question_id": question},
                        "condition": {"target": target, "repetition": repetition},
                        "conversation": {"fresh": True},
                        "native_execution": {"used_only_declared_surface": True, "fallback_used": False},
                        "candidate": {"statement_count": 1},
                        "evaluation": {
                            "execution_success": True,
                            "result_equivalent": correct,
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


def test_publication_matrix_and_unavailable_tokens() -> None:
    rows = _records()
    assert len(rows) == EXPECTED_TRIALS == 216
    report = evaluate_execution(rows, publication=True)
    assert report["trial_count"] == 216
    assert report["question_denominator"] == 12
    assert report["global_winner"] is None
    blank = report["targets"]["blank_context"]
    assert blank["execution_accuracy"] == 1.0
    assert blank["tokens"]["input_tokens"]["unavailable_trials"] == 12
    assert blank["tokens"]["cached_input_tokens"]["total"] is None
    assert blank["three_run_consistency"] == 1.0


def test_publication_fails_closed_on_missing_trial() -> None:
    rows = _records()
    rows.pop()
    with pytest.raises(ExecutionEvaluationError, match="exactly 216"):
        evaluate_execution(rows, publication=True)


def test_publication_fails_closed_on_context_reuse() -> None:
    rows = _records()
    rows[0]["conversation"]["fresh"] = False
    with pytest.raises(ExecutionEvaluationError, match="Fresh-context"):
        evaluate_execution(rows, publication=True)


def test_multi_formulation_questions_keep_one_question_denominator() -> None:
    report = evaluate_execution(_records(), publication=True)
    assert report["question_denominator"] == 12
    for comparison in report["paired_comparisons"].values():
        assert comparison["question_pairs"] == 12
