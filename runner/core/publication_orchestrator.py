"""Materialize closed native candidates into publication benchmark artifacts.

This module is evaluator-side. It accepts only the sanitized output returned by
``run_native_trial`` after that function has closed its provider and runtime.
Gold files are opened here, never by the target runtime or agent provider.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker


class PublicationOrchestrationError(RuntimeError):
    """Raised when an artifact cannot satisfy publication invariants."""


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _token(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _error_category(value: Any, *, fallback: str | None = None) -> str | None:
    allowed = {
        "preflight", "native_validation", "unsupported_semantics", "agent_protocol",
        "tool_error", "sql_policy", "sql_parse", "sql_bind", "sql_runtime",
        "timeout", "wrong_result", "incomplete_result", "internal",
    }
    if value in allowed:
        return value
    if value == "protocol_violation":
        return "agent_protocol"
    if value == "turn_budget":
        return "timeout"
    return fallback


def _combined_result_sha256(values: Sequence[str]) -> str:
    if not values or any(not isinstance(value, str) or len(value) != 64 for value in values):
        raise PublicationOrchestrationError("Result identity must contain one or more SHA-256 values")
    return _canonical_sha256({"normalization_revision": "canonical-json-v1", "statements": list(values)})


def _validate(instance: Mapping[str, Any], schema_path: Path, label: str) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        location = ".".join(str(part) for part in errors[0].absolute_path) or "<root>"
        raise PublicationOrchestrationError(f"{label} is invalid at {location}: {errors[0].message}")


def load_gold_for_candidate(
    candidate: Mapping[str, Any],
    *,
    gold_path: str | Path,
    gold_pack_path: str | Path,
    root: str | Path = ".",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load one Gold file and prove that it belongs to the frozen pack/candidate."""

    root_path = Path(root).resolve()
    gold_file = Path(gold_path)
    pack_file = Path(gold_pack_path)
    if not gold_file.is_absolute():
        gold_file = root_path / gold_file
    if not pack_file.is_absolute():
        pack_file = root_path / pack_file
    gold_file = gold_file.resolve()
    pack_file = pack_file.resolve()
    if not gold_file.is_relative_to(root_path) or not pack_file.is_relative_to(root_path):
        raise PublicationOrchestrationError("Gold inputs must remain inside the repository root")

    gold = json.loads(gold_file.read_text(encoding="utf-8"))
    pack = json.loads(pack_file.read_text(encoding="utf-8"))
    question = candidate.get("question", {})
    question_id = question.get("question_id")
    instance_id = question.get("instance_id")
    if gold.get("question_id") != question_id or gold.get("instance_id") != instance_id:
        raise PublicationOrchestrationError("Gold question identity does not match the candidate")

    entries = [entry for entry in pack.get("gold", []) if entry.get("question_id") == question_id]
    if len(entries) != 1:
        raise PublicationOrchestrationError("Gold pack must resolve the candidate question exactly once")
    entry = entries[0]
    declared_path = (root_path / entry["path"]).resolve()
    if declared_path != gold_file or _sha256_file(gold_file) != entry.get("sha256"):
        raise PublicationOrchestrationError("Gold file does not match its frozen pack entry")
    return gold, pack


def materialize_publication_trial(
    *,
    run_id: str,
    experiment_id: str,
    lane: str,
    candidate: Mapping[str, Any],
    native_trace: Sequence[Mapping[str, Any]],
    gold: Mapping[str, Any],
    output_dir: str | Path,
    contracts_dir: str | Path,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Evaluate a closed candidate and write one schema-valid publication trial."""

    conversation = candidate.get("conversation", {})
    provider = candidate.get("provider", {})
    unavailable = provider.get("kind") == "unavailable" and candidate.get("status") != "candidate_ready"
    if conversation.get("provider_closed_before_evaluation") is not True:
        raise PublicationOrchestrationError("Gold evaluation requires a closed provider/runtime")
    if not unavailable and (provider.get("kind") != "live" or provider.get("ranking_eligible") is not True):
        raise PublicationOrchestrationError("Publication trials require a ranking-eligible live provider")
    response_ids = conversation.get("provider_response_ids")
    if not isinstance(response_ids, list) or (not response_ids and candidate.get("status") == "candidate_ready"):
        raise PublicationOrchestrationError("Publication trials require provider response identities")

    question = candidate.get("question", {})
    if gold.get("question_id") != question.get("question_id") or gold.get("instance_id") != question.get("instance_id"):
        raise PublicationOrchestrationError("Candidate and Gold identities differ")
    gold_hashes = [statement["result"]["sha256"] for statement in gold.get("statements", [])]
    result_artifacts = candidate.get("candidate", {}).get("result_artifacts", [])
    candidate_hashes = [entry.get("result_sha256") for entry in result_artifacts]
    if len(candidate_hashes) != len(gold_hashes):
        equivalent = False
        candidate_combined = None
    else:
        candidate_combined = _combined_result_sha256(candidate_hashes)
        equivalent = candidate_hashes == gold_hashes
    reference_combined = _combined_result_sha256(gold_hashes)

    trial_id = str(candidate.get("trial_id") or "")
    if not run_id or not experiment_id or not trial_id:
        raise PublicationOrchestrationError("run_id, experiment_id, and trial_id are required")
    created_at = timestamp or _utc_now()
    destination = Path(output_dir) / "trials" / trial_id
    destination.mkdir(parents=True, exist_ok=False)

    transcript_path = destination / "conversation.sanitized.jsonl"
    transcript_rows = conversation.get("message_manifest", [])
    transcript_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in transcript_rows), encoding="utf-8"
    )

    error = candidate.get("error", {})
    candidate_status = candidate.get("status")
    if candidate_status == "candidate_ready":
        status = "passed" if equivalent else "failed"
        error_category = None if equivalent else "wrong_result"
    elif unavailable:
        status = "invalid"
        error_category = _error_category(error.get("category"), fallback="preflight")
    elif candidate_status in {"unsupported", "timeout", "invalid"}:
        status = candidate_status
        error_category = _error_category(error.get("category"), fallback="internal")
    else:
        status = "failed"
        error_category = _error_category(error.get("category"), fallback="internal")

    sql_artifacts = candidate.get("candidate", {}).get("sql_artifacts", [])
    record = {
        "schema_version": "0.1.0",
        "run_id": run_id,
        "trial_id": trial_id,
        "experiment_id": experiment_id,
        "question": {
            "question_id": question["question_id"],
            "instance_id": question["instance_id"],
            "target_prompt_sha256": question["question_sha256"],
        },
        "condition": {
            "target": candidate["condition"]["target"],
            "lane": lane,
            "repetition": candidate["condition"]["repetition"],
            "native_surface": candidate["condition"]["native_surface"],
            "artifact_sha256": candidate["condition"].get("artifact_sha256"),
            "adapter_version": candidate["condition"].get("adapter_version"),
        },
        "conversation": {
            "fresh": True,
            "system_prompt_sha256": conversation["system_prompt_sha256"],
            "tool_schema_sha256": conversation["tool_schema_sha256"],
            "sanitized_transcript": transcript_path.as_posix(),
            "message_count": conversation["message_count"],
            "provider_conversation_id": "conv-" + _canonical_sha256({"run_id": run_id, "trial_id": trial_id}),
            "provider_response_ids": response_ids,
        },
        "native_execution": candidate["native_execution"],
        "candidate": {
            "statement_count": len(candidate_hashes),
            "sql_artifacts": [f"sha256:{entry['sql_sha256']}" for entry in sql_artifacts],
            "result_artifacts": [f"sha256:{value}" for value in candidate_hashes if isinstance(value, str)],
            "answer_artifact": None,
        },
        "evaluation": {
            "execution_success": candidate_status == "candidate_ready" and bool(candidate_hashes),
            "result_equivalent": equivalent if candidate_status == "candidate_ready" else None,
            "reference_result_sha256": reference_combined,
            "candidate_result_sha256": candidate_combined,
            "error_category": error_category,
            "error_detail": error.get("detail"),
        },
        "usage": {
            "input_tokens": _token(candidate["usage"].get("input_tokens")),
            "output_tokens": _token(candidate["usage"].get("output_tokens")),
            "cached_input_tokens": _token(candidate["usage"].get("cached_input_tokens")),
            "tool_calls": candidate["usage"]["tool_calls"],
            "database_calls": candidate["usage"]["database_calls"],
            "total_latency_ms": candidate["usage"]["total_latency_ms"],
            "evaluator_latency_ms": 0.0,
        },
        "status": status,
    }
    contracts = Path(contracts_dir)
    _validate(record, contracts / "trial-record.schema.json", "Trial record")
    (destination / "trial.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    trace_rows = []
    event_map = {
        "trial.start": "trial.start", "target.preflight": "native.bootstrap",
        "context.initial": "context.read", "conversation.start": "llm.request",
        "llm.generate": "llm.response", "tool.call": "tool.call",
        "conversation.close": "tool.result", "trial.finish": "trial.end",
    }
    for sequence, event in enumerate(native_trace):
        trace_rows.append({
            "schema_version": "0.1.0", "run_id": run_id, "trial_id": trial_id,
            "sequence": sequence, "timestamp": created_at,
            "event_type": event_map.get(str(event.get("event_type")), "tool.result"),
            "status": event.get("status") if event.get("status") in {"started", "ok", "error", "timeout", "unsupported", "skipped"} else "error",
            "duration_ms": event.get("duration_ms"), "attributes": dict(event.get("attributes", {})),
            "redaction_applied": True,
        })
    if not trace_rows or trace_rows[0]["event_type"] != "trial.start" or trace_rows[-1]["event_type"] != "trial.end":
        raise PublicationOrchestrationError("Native trace must span trial.start through trial.end")
    for row in trace_rows:
        _validate(row, contracts / "trace-event.schema.json", "Trace event")
    (destination / "trace.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in trace_rows), encoding="utf-8"
    )
    return record


def build_publication_manifest(
    *,
    run_id: str,
    experiment_id: str,
    dataset_manifest_sha256: str,
    gold_pack_path: str | Path,
    provider: str,
    model: str,
    trials: Sequence[Mapping[str, Any]],
    contracts_dir: str | Path,
    status: str = "completed",
    finished_at: str | None = None,
) -> dict[str, Any]:
    """Bind a closed publication run to every tool schema and Gold identity."""

    tool_schemas: dict[str, str] = {}
    gold_results: dict[str, str] = {}
    for trial in trials:
        target = trial["condition"]["target"]
        tool_hash = trial["conversation"]["tool_schema_sha256"]
        if target in tool_schemas and tool_schemas[target] != tool_hash:
            raise PublicationOrchestrationError(f"Tool schema changed within target {target}")
        tool_schemas[target] = tool_hash
        question = trial["question"]["question_id"]
        gold_hash = trial["evaluation"]["reference_result_sha256"]
        if question in gold_results and gold_results[question] != gold_hash:
            raise PublicationOrchestrationError(f"Gold identity changed within question {question}")
        gold_results[question] = gold_hash
    manifest = {
        "schema_version": "0.1.0", "run_id": run_id, "experiment_id": experiment_id,
        "status": status, "finished_at": finished_at or _utc_now(),
        "dataset_manifest_sha256": dataset_manifest_sha256,
        "gold_pack_sha256": _sha256_file(Path(gold_pack_path)),
        "provider": provider, "model": model,
        "tool_schema_sha256_by_target": tool_schemas,
        "gold_result_sha256_by_question": gold_results,
        "trial_count": len(trials),
    }
    _validate(manifest, Path(contracts_dir) / "publication-run-manifest.schema.json", "Publication manifest")
    return manifest
