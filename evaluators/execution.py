from __future__ import annotations

from collections import Counter, defaultdict
from math import ceil, comb
from random import Random
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence


QUESTION_IDS = ("q01", "q02", "q03", "q05", "q12", "q14", "q21", "q36", "q39", "q49", "q75", "q84")
TARGETS = ("blank_context", "ddl_only", "metricflow", "ossie", "okf", "skill")
REPETITIONS = (1, 2, 3)
EXPECTED_TRIALS = len(QUESTION_IDS) * len(TARGETS) * len(REPETITIONS)
BOOTSTRAP_SEED = 20260914
BOOTSTRAP_SAMPLES = 20_000


class ExecutionEvaluationError(RuntimeError):
    pass


def _p95(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(0, ceil(0.95 * len(ordered)) - 1)], 3)


def _mean(values: Iterable[float]) -> float | None:
    materialized = list(values)
    return round(mean(materialized), 3) if materialized else None


def _token_summary(records: Sequence[Mapping[str, Any]], field: str) -> dict[str, Any]:
    values = [record["usage"].get(field) for record in records]
    known = [int(value) for value in values if value is not None]
    return {
        "available_trials": len(known),
        "unavailable_trials": len(values) - len(known),
        "total": sum(known) if known else None,
        "mean": _mean(known),
    }


def _sign_test_p_value(wins: int, losses: int) -> float | None:
    n = wins + losses
    if n < 5:
        return None
    k = min(wins, losses)
    tail = sum(comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def _percentile(sorted_values: Sequence[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("percentile requires values")
    index = probability * (len(sorted_values) - 1)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = index - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def _paired_bootstrap_ci(deltas: Sequence[float]) -> list[float] | None:
    """Question-level paired percentile bootstrap CI with a fixed seed.

    The resampling unit is one benchmark question, never an individual repetition.
    """

    if len(deltas) < 2:
        return None
    rng = Random(BOOTSTRAP_SEED)
    size = len(deltas)
    samples = sorted(mean(deltas[rng.randrange(size)] for _ in range(size)) for _ in range(BOOTSTRAP_SAMPLES))
    return [round(_percentile(samples, 0.025), 6), round(_percentile(samples, 0.975), 6)]


def validate_publication_trials(
    records: Sequence[Mapping[str, Any]],
    *,
    run_manifest: Mapping[str, Any] | None,
) -> None:
    if len(records) != EXPECTED_TRIALS:
        raise ExecutionEvaluationError(f"Representative publication requires exactly {EXPECTED_TRIALS} trials")
    if not isinstance(run_manifest, Mapping):
        raise ExecutionEvaluationError("Publication requires a validated run manifest")

    required_manifest_fields = (
        "run_id",
        "experiment_id",
        "status",
        "finished_at",
        "dataset_manifest_sha256",
        "gold_pack_sha256",
        "provider",
        "model",
        "tool_schema_sha256_by_target",
        "gold_result_sha256_by_question",
    )
    missing = [field for field in required_manifest_fields if not run_manifest.get(field)]
    if missing:
        raise ExecutionEvaluationError(f"Publication run manifest is incomplete: {', '.join(missing)}")
    if run_manifest["status"] not in {"completed", "completed_with_failures"}:
        raise ExecutionEvaluationError("Publication run manifest is not lifecycle-closed")

    tool_schemas = run_manifest["tool_schema_sha256_by_target"]
    gold_results = run_manifest["gold_result_sha256_by_question"]
    if set(tool_schemas) != set(TARGETS):
        raise ExecutionEvaluationError("Publication run manifest must bind every target tool schema")
    if set(gold_results) != set(QUESTION_IDS):
        raise ExecutionEvaluationError("Publication run manifest must bind every question Gold result")

    seen: set[tuple[str, str, int]] = set()
    conversation_ids: set[str] = set()
    response_ids: set[str] = set()
    trial_ids: set[str] = set()
    for record in records:
        key = (
            str(record["question"]["question_id"]),
            str(record["condition"]["target"]),
            int(record["condition"]["repetition"]),
        )
        if key in seen:
            raise ExecutionEvaluationError(f"Duplicate representative trial: {key}")
        seen.add(key)
        question, target, repetition = key
        if question not in QUESTION_IDS or target not in TARGETS or repetition not in REPETITIONS:
            raise ExecutionEvaluationError(f"Unexpected representative trial: {key}")
        if record.get("run_id") != run_manifest["run_id"] or record.get("experiment_id") != run_manifest["experiment_id"]:
            raise ExecutionEvaluationError(f"Run identity invariant failed: {key}")

        trial_id = str(record.get("trial_id") or "")
        if not trial_id or trial_id in trial_ids:
            raise ExecutionEvaluationError(f"Unique trial identity invariant failed: {key}")
        trial_ids.add(trial_id)

        conversation = record["conversation"]
        if conversation.get("fresh") is not True:
            raise ExecutionEvaluationError(f"Fresh-context invariant failed: {key}")
        conversation_id = conversation.get("provider_conversation_id")
        if not isinstance(conversation_id, str) or not conversation_id or conversation_id in conversation_ids:
            raise ExecutionEvaluationError(f"Unique conversation identity invariant failed: {key}")
        conversation_ids.add(conversation_id)
        provider_response_ids = conversation.get("provider_response_ids")
        if not isinstance(provider_response_ids, list) or not provider_response_ids:
            raise ExecutionEvaluationError(f"Conversation lifecycle closure invariant failed: {key}")
        for response_id in provider_response_ids:
            if not isinstance(response_id, str) or not response_id or response_id in response_ids:
                raise ExecutionEvaluationError(f"Unique provider response identity invariant failed: {key}")
            response_ids.add(response_id)
        if conversation.get("tool_schema_sha256") != tool_schemas[target]:
            raise ExecutionEvaluationError(f"Tool-schema identity invariant failed: {key}")

        if record["evaluation"].get("reference_result_sha256") != gold_results[question]:
            raise ExecutionEvaluationError(f"Frozen Gold binding invariant failed: {key}")
        if record["native_execution"].get("used_only_declared_surface") is not True:
            raise ExecutionEvaluationError(f"Tool allowlist invariant failed: {key}")
        if record["native_execution"].get("fallback_used") is not False:
            raise ExecutionEvaluationError(f"Fallback invariant failed: {key}")

    expected = {(q, t, r) for q in QUESTION_IDS for t in TARGETS for r in REPETITIONS}
    if seen != expected:
        raise ExecutionEvaluationError("Representative trial matrix is incomplete")


def evaluate_execution(
    records: Sequence[Mapping[str, Any]],
    *,
    publication: bool = True,
    run_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if publication:
        validate_publication_trials(records, run_manifest=run_manifest)

    by_target: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        by_target[str(record["condition"]["target"])].append(record)

    targets: dict[str, Any] = {}
    for target in TARGETS:
        rows = by_target.get(target, [])
        equivalent = [row for row in rows if row["evaluation"].get("result_equivalent") is True]
        executable = [row for row in rows if row["evaluation"].get("execution_success") is True]
        complete = [row for row in rows if row["candidate"].get("statement_count", 0) > 0 and row["status"] not in {"invalid", "skipped"}]
        consistency: list[float] = []
        for question in QUESTION_IDS:
            qrows = [row for row in rows if row["question"]["question_id"] == question]
            if len(qrows) != 3:
                continue
            outcomes = [row["evaluation"].get("result_equivalent") for row in qrows]
            consistency.append(1.0 if len(set(outcomes)) == 1 else 0.0)
        errors = Counter(row["evaluation"].get("error_category") or "none" for row in rows)
        targets[target] = {
            "trial_count": len(rows),
            "execution_accuracy": round(len(equivalent) / len(rows), 6) if rows else None,
            "sql_execution_rate": round(len(executable) / len(rows), 6) if rows else None,
            "answer_completeness": round(len(complete) / len(rows), 6) if rows else None,
            "three_run_consistency": _mean(consistency),
            "tokens": {field: _token_summary(rows, field) for field in ("input_tokens", "output_tokens", "cached_input_tokens")},
            "tool_calls": {"mean": _mean(float(row["usage"]["tool_calls"]) for row in rows), "total": sum(row["usage"]["tool_calls"] for row in rows)},
            "database_calls": {"mean": _mean(float(row["usage"]["database_calls"]) for row in rows), "total": sum(row["usage"]["database_calls"] for row in rows)},
            "latency_ms": {"mean": _mean(float(row["usage"]["total_latency_ms"]) for row in rows), "p95": _p95([float(row["usage"]["total_latency_ms"]) for row in rows])},
            "error_categories": dict(sorted(errors.items())),
        }

    paired: dict[str, Any] = {}
    for left_index, left in enumerate(TARGETS):
        for right in TARGETS[left_index + 1 :]:
            wins = losses = ties = 0
            deltas: list[float] = []
            for question in QUESTION_IDS:
                left_values = [1.0 if row["evaluation"].get("result_equivalent") is True else 0.0 for row in by_target.get(left, []) if row["question"]["question_id"] == question]
                right_values = [1.0 if row["evaluation"].get("result_equivalent") is True else 0.0 for row in by_target.get(right, []) if row["question"]["question_id"] == question]
                if not left_values or not right_values:
                    continue
                delta = mean(left_values) - mean(right_values)
                deltas.append(delta)
                wins += delta > 0
                losses += delta < 0
                ties += delta == 0
            avg = mean(deltas) if deltas else None
            paired[f"{left}__vs__{right}"] = {
                "question_pairs": len(deltas),
                "unit_of_analysis": "question",
                "accuracy_delta": round(avg, 6) if avg is not None else None,
                "paired_95pct_ci": _paired_bootstrap_ci(deltas),
                "paired_95pct_ci_method": "paired percentile bootstrap over question-level deltas",
                "bootstrap_samples": BOOTSTRAP_SAMPLES if len(deltas) >= 2 else None,
                "bootstrap_seed": BOOTSTRAP_SEED if len(deltas) >= 2 else None,
                "wins": wins,
                "losses": losses,
                "ties": ties,
                "two_sided_sign_test_p": _sign_test_p_value(wins, losses),
            }

    return {
        "schema_version": "0.1.0",
        "benchmark": "TPC-DS-derived",
        "suite": "representative-v1",
        "trial_count": len(records),
        "question_denominator": len(QUESTION_IDS),
        "repetitions": 3,
        "targets": targets,
        "paired_comparisons": paired,
        "global_winner": None,
    }
