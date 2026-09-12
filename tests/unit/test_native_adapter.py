from __future__ import annotations

import pytest

from runner.core.native_adapter import (
    NativeIsolationError,
    NativeOperationError,
    TargetQuestion,
    assert_declared_operation,
    assert_native_artifact_root,
)


def test_target_question_strips_evaluator_and_orchestrator_fields() -> None:
    instance = {
        "question_id": "q01",
        "instance_id": "sf1-q01",
        "target_input": {"question": "What is the answer?"},
        "orchestrator_only": {"parameters": [{"name": "secret"}]},
        "evaluator_only": {"reference_sql": ["never expose this"]},
    }

    context = TargetQuestion.from_instance(instance).provider_context()

    assert context == {
        "question_id": "q01",
        "instance_id": "sf1-q01",
        "question": "What is the answer?",
    }
    assert "reference_sql" not in repr(context)
    assert "parameters" not in repr(context)


def test_target_question_rejects_extra_target_input_fields() -> None:
    with pytest.raises(NativeIsolationError, match="exactly"):
        TargetQuestion.from_instance(
            {
                "question_id": "q01",
                "instance_id": "sf1-q01",
                "target_input": {"question": "safe", "reference_sql": "unsafe"},
            }
        )


def test_adapter_operations_are_closed_and_gold_is_forbidden() -> None:
    target = {
        "allowed_operations": ["metricflow.query", "benchmark.submit_result"],
        "prohibited_operations": ["db.execute_readonly", "benchmark.read_gold"],
    }

    assert_declared_operation(target, "metricflow.query")
    with pytest.raises(NativeOperationError, match="Undeclared"):
        assert_declared_operation(target, "metricflow.list_metrics")
    with pytest.raises(NativeIsolationError, match="Prohibited"):
        assert_declared_operation(target, "benchmark.read_gold")


def test_adapter_rejects_evaluator_only_artifact_roots() -> None:
    assert_native_artifact_root("semantic-models/metricflow/tpcds-sf1")
    with pytest.raises(NativeIsolationError):
        assert_native_artifact_root("benchmark/tpcds/results/gold/sf1")
