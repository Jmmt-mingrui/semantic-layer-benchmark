from __future__ import annotations

from collections import Counter, defaultdict
from math import ceil, comb
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence


QUESTION_IDS = ("q01", "q02", "q03", "q05", "q12", "q14", "q21", "q36", "q39", "q49", "q75", "q84")
TARGETS = ("blank_context", "ddl_only", "metricflow", "ossie", "okf", "skill")
REPETITIONS = (1, 2, 3)
EXPECTED_TRIALS = len(QUESTION_IDS) * len(TARGETS) * len(REPETITIONS)


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


def validate_publication_trials(records: Sequence[Mapping[str, Any]]) -> None:
    if len(records) != EXPECTED_TRIALS:
        raise ExecutionEvaluationError(f"Representative publication requires exactly {EXPECTED_TRIALS} trials")
    seen: set[tuple[str, str, int]] = set()
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
        if record["conversation"].get("fresh") is not True:
            raise ExecutionEvaluationError(f"Fresh-context invariant failed: {key}")
        if record["native_execution"].get("used_only_declared_surface") is not True:
            raise ExecutionEvaluationError(f"Tool allowlist invariant failed: {key}")
        if record["native_execution"].get("fallback_used") is not False:
            raise ExecutionEvaluationError(f"Fallback invariant failed: {key}")
    expected = {(q, t, r) for q in QUESTION_IDS for t in TARGETS for r in REPETITIONS}
    if seen != expected:
        raise ExecutionEvaluationError("Representative trial matrix is incomplete")


def evaluate_execution(records: Sequence[Mapping[str, Any]], *, publication: bool = True) -> dict[str, Any]:
    if publication:
        validate_publication_trials(records)

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
            # Question-level paired interval: normal approximation around the 12
            # question deltas. It is descriptive and kept separate from rankings.
            if len(deltas) >= 2:
                avg = mean(deltas)
                variance = sum((value - avg) ** 2 for value in deltas) / (len(deltas) - 1)
                margin = 1.96 * (variance / len(deltas)) ** 0.5
                ci = [round(avg - margin, 6), round(avg + margin, 6)]
            else:
                avg, ci = None, None
            paired[f"{left}__vs__{right}"] = {
                "question_pairs": len(deltas),
                "accuracy_delta": round(avg, 6) if avg is not None else None,
                "paired_95pct_ci": ci,
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
