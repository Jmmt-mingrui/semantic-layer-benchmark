from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import random
import subprocess
from time import perf_counter
from typing import Any
from uuid import uuid4

from jsonschema import Draft202012Validator
import yaml

from runner.core.agent import AgentProvider
from runner.core.control_tools import ControlToolDispatcher, ToolProtocolError, ToolTimeoutError, result_sha256
from runner.core.database import DatabaseSettings, connect, duckdb_path_from_url, load_database_settings
from runner.core.native_adapter import TargetQuestion


ProviderFactory = Callable[[str, int, dict[str, Any]], AgentProvider]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sha256_bytes(content: bytes) -> str:
    return sha256(content).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _path_ref(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _jsonl_dump(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n" for value in values))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _repository_sha(root: Path) -> str:
    configured = os.getenv("BENCHMARK_REPOSITORY_SHA")
    if configured:
        if len(configured) != 40 or any(char not in "0123456789abcdef" for char in configured):
            raise ValueError("BENCHMARK_REPOSITORY_SHA must be a lowercase 40-character SHA")
        return configured
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def _memory_limit_mb() -> int:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return max(1, int(pages * page_size / (1024 * 1024)))
    except (ValueError, OSError, AttributeError):
        return 1


def _render_user_prompt(template: str, question: str) -> str:
    if template.count("{{question}}") != 1:
        raise ValueError("User prompt template must contain {{question}} exactly once")
    return template.replace("{{question}}", question)


def _resolve_env(spec: Any) -> Any:
    if not isinstance(spec, dict) or "env" not in spec:
        return spec
    value = os.getenv(str(spec["env"]))
    if value not in (None, ""):
        return value
    if "default" in spec:
        return spec["default"]
    if spec.get("required"):
        raise ValueError(f"Required environment variable is not set: {spec['env']}")
    return None


def _ddl_context(root: Path, artifact_root: str) -> tuple[str, str]:
    paths = sorted((root / artifact_root).rglob("*.sql"))
    if not paths:
        raise ValueError(f"No DDL files found under {artifact_root}")
    sections = [f"-- Source: {path.relative_to(root)}\n{path.read_text().rstrip()}" for path in paths]
    content = "\n\n".join(sections) + "\n"
    return content, _sha256_bytes(content.encode())


class TraceRecorder:
    def __init__(self, run_id: str, trial_id: str):
        self.run_id = run_id
        self.trial_id = trial_id
        self.events: list[dict[str, Any]] = []

    def add(
        self,
        event_type: str,
        status: str,
        *,
        duration_ms: float | None = None,
        attributes: dict[str, Any] | None = None,
        usage: dict[str, Any] | None = None,
        artifact_refs: list[dict[str, Any]] | None = None,
    ) -> None:
        event: dict[str, Any] = {
            "schema_version": "0.1.0",
            "run_id": self.run_id,
            "trial_id": self.trial_id,
            "sequence": len(self.events),
            "timestamp": _utc_now(),
            "event_type": event_type,
            "status": status,
            "attributes": attributes or {},
        }
        if duration_ms is not None:
            event["duration_ms"] = duration_ms
        if usage is not None:
            event["usage"] = usage
        if artifact_refs is not None:
            event["artifact_refs"] = artifact_refs
        self.events.append(event)


def run_control_experiment(
    config_path: str | Path,
    provider_factory: ProviderFactory,
    *,
    root: str | Path = ".",
) -> Path:
    root_path = Path(root).resolve()
    config_file = (root_path / config_path).resolve() if not Path(config_path).is_absolute() else Path(config_path)
    config = yaml.safe_load(config_file.read_text())
    Draft202012Validator(_load_schema(root_path / "runner/contracts/experiment.schema.json")).validate(config)

    targets = list(config["targets"]["include"])
    unsupported = sorted(set(targets) - {"blank_context", "ddl_only"})
    if unsupported:
        raise ValueError(f"Control runner only accepts blank_context and ddl_only: {unsupported}")

    registry_path = root_path / config["targets"]["registry"]
    registry = yaml.safe_load(registry_path.read_text())
    tool_path = root_path / registry["targets"]["blank_context"]["native_surface"]["tool_catalog"]
    tool_catalog = json.loads(tool_path.read_text())
    questions_path = root_path / config["workload"]["question_instances"]
    questions = _load_jsonl(questions_path)
    selected = [row for row in questions if row["question_id"] in config["workload"]["question_ids"]]
    if len(selected) != len(config["workload"]["question_ids"]):
        raise ValueError("Every configured question ID must resolve to exactly one instance")
    question_schema = _load_schema(root_path / "runner/contracts/question-instance.schema.json")
    for question in selected:
        Draft202012Validator(question_schema).validate(question)
        result_contract = question["evaluator_only"]["result_contract"]
        if (
            question["evaluator_only"]["expected_statement_count"] != 1
            or result_contract["comparison"] != "exact_normalized"
            or not result_contract["order_sensitive"]
        ):
            raise ValueError(
                "Control runner v0.1 supports one-statement, order-sensitive, exact-normalized questions only"
            )

    manifest_path = root_path / config["dataset"]["manifest"]
    manifest = json.loads(manifest_path.read_text())
    Draft202012Validator(_load_schema(root_path / "runner/contracts/dataset-manifest.schema.json")).validate(manifest)
    expected_dataset_sha = _resolve_env(config["dataset"].get("snapshot_sha256"))
    if expected_dataset_sha != manifest["dataset_sha256"]:
        raise ValueError("Configured dataset SHA does not match the manifest")

    system_path = root_path / config["agent"]["system_prompt"]
    user_template_path = root_path / config["agent"]["user_prompt_template"]
    system_prompt = system_path.read_text().rstrip()
    user_template = user_template_path.read_text().rstrip()
    _resolve_env(config["agent"]["provider"])
    _resolve_env(config["agent"]["model"])
    _resolve_env(config["agent"].get("model_revision"))
    run_id = f"run-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    run_dir = root_path / config["artifacts"]["run_directory"] / run_id
    started_at = _utc_now()
    trial_paths: list[str] = []
    statuses: list[str] = []

    database_settings = load_database_settings(root_path / config["dataset"]["database_config"])
    database_path = duckdb_path_from_url(database_settings.url)
    if database_path != ":memory:":
        resolved_database = Path(database_path)
        if not resolved_database.is_absolute():
            resolved_database = root_path / resolved_database
        if not resolved_database.is_file():
            raise ValueError(f"Database file does not exist: {resolved_database}")
        if _file_sha256(resolved_database) != manifest["database"]["sha256"]:
            raise ValueError("Database file SHA does not match the dataset manifest")
        database_settings = DatabaseSettings(
            database_settings.driver,
            f"duckdb://{resolved_database}",
            database_settings.catalog,
            database_settings.schema,
            database_settings.read_only,
        )
    target_order = list(targets)
    question_order = list(selected)
    order_random = random.Random(int(config["execution"].get("random_seed", 0)))
    if config["execution"]["target_order"] == "randomized":
        order_random.shuffle(target_order)
    if config["execution"]["question_order"] == "randomized":
        order_random.shuffle(question_order)

    with connect(database_settings) as database:
        for repetition in range(1, int(config["execution"]["repetitions"]) + 1):
            for target in target_order:
                target_config = registry["targets"][target]
                for question in question_order:
                    trial_id = f"{question['instance_id']}-{target}-r{repetition:02d}"
                    trial_dir = run_dir / "trials" / trial_id
                    trace = TraceRecorder(run_id, trial_id)
                    trace.add("trial.start", "started", attributes={"target": target, "repetition": repetition})
                    initial_messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
                    artifact_sha: str | None = None
                    if target == "ddl_only":
                        ddl, artifact_sha = _ddl_context(root_path, target_config["native_surface"]["artifact_root"])
                        initial_messages.append(
                            {"role": "system", "content": "Physical database DDL for this trial:\n\n" + ddl}
                        )
                        trace.add("context.read", "ok", attributes={"kind": "physical_ddl", "sha256": artifact_sha})
                    rendered_user = _render_user_prompt(user_template, question["target_input"]["question"])
                    initial_messages.append({"role": "user", "content": rendered_user})
                    provider = provider_factory(target, repetition, TargetQuestion.from_instance(question).provider_context())
                    allowed = set(target_config["allowed_operations"])
                    dispatcher = ControlToolDispatcher(
                        database,
                        tool_catalog,
                        allowed,
                        max_database_attempts=int(config["execution"].get("max_database_attempts", 3)),
                        database_timeout_seconds=float(config["execution"]["timeouts"]["database_seconds"]),
                    )
                    trial = _run_trial(
                        root_path,
                        config,
                        question,
                        target,
                        target_config,
                        provider,
                        dispatcher,
                        initial_messages,
                        trace,
                        trial_dir,
                        artifact_sha,
                    )
                    relative_trial = _path_ref(trial_dir / "trial.json", root_path)
                    _json_dump(trial_dir / "trial.json", trial)
                    _jsonl_dump(trial_dir / "trace.jsonl", trace.events)
                    Draft202012Validator(_load_schema(root_path / "runner/contracts/trial-record.schema.json")).validate(trial)
                    trace_schema = _load_schema(root_path / "runner/contracts/trace-event.schema.json")
                    for event in trace.events:
                        Draft202012Validator(trace_schema).validate(event)
                    trial_paths.append(relative_trial)
                    statuses.append(trial["status"])

    summary = {name: statuses.count(name) for name in ("passed", "failed", "unsupported", "invalid", "timeout")}
    run_record = {
        "schema_version": "0.1.0",
        "run_id": run_id,
        "experiment_id": config["experiment_id"],
        "started_at": started_at,
        "finished_at": _utc_now(),
        "reproducibility": {
            "repository_sha": _repository_sha(root_path),
            "experiment_sha256": _file_sha256(config_file),
            "dataset_manifest_sha256": _file_sha256(manifest_path),
            "target_registry_sha256": _file_sha256(registry_path),
            "prompt_sha256": _file_sha256(system_path),
            "question_instances_sha256": _file_sha256(questions_path),
        },
        "environment": {
            "os": platform.platform(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "database": f"duckdb {__import__('duckdb').__version__}",
            "container_image_digest": os.getenv("BENCHMARK_CONTAINER_IMAGE_DIGEST"),
            "cpu_limit": float(os.getenv("BENCHMARK_CPU_LIMIT", os.cpu_count() or 1)),
            "memory_limit_mb": int(os.getenv("BENCHMARK_MEMORY_LIMIT_MB", _memory_limit_mb())),
        },
        "trial_records": trial_paths,
        "summary": {
            "planned": len(statuses),
            "completed": len(statuses),
            **summary,
        },
        "status": "completed" if all(value == "passed" for value in statuses) else "completed_with_failures",
    }
    Draft202012Validator(_load_schema(root_path / "runner/contracts/run-record.schema.json")).validate(run_record)
    _json_dump(run_dir / "run.json", run_record)
    return run_dir / "run.json"


def _run_trial(
    root_path: Path,
    config: dict[str, Any],
    question: dict[str, Any],
    target: str,
    target_config: dict[str, Any],
    provider: AgentProvider,
    dispatcher: ControlToolDispatcher,
    messages: list[dict[str, Any]],
    trace: TraceRecorder,
    trial_dir: Path,
    artifact_sha: str | None,
) -> dict[str, Any]:
    started = perf_counter()
    transcript = list(messages)
    native_requests: list[dict[str, Any]] = []
    response_ids: list[str] = []
    input_tokens = output_tokens = cached_tokens = 0
    usage_known = True
    error_category: str | None = None
    tools = dispatcher.public_tools()
    generation = config["agent"]["generation"]
    for _ in range(int(generation["max_turns"])):
        remaining_seconds = float(config["execution"]["timeouts"]["trial_seconds"]) - (perf_counter() - started)
        if remaining_seconds <= 0:
            error_category = "timeout"
            break
        trace.add("llm.request", "started", attributes={"message_count": len(messages)})
        turn_started = perf_counter()
        try:
            turn = provider.complete(
                tuple(messages),
                tuple(tools),
                generation,
                min(float(config["execution"]["timeouts"]["tool_seconds"]), remaining_seconds),
            )
        except Exception as exc:
            error_category = "agent_protocol"
            trace.add("llm.response", "error", duration_ms=(perf_counter() - turn_started) * 1000, attributes={"error": str(exc)})
            break
        usage = turn.usage
        if None in (usage.input_tokens, usage.output_tokens, usage.cached_input_tokens):
            usage_known = False
        input_tokens += usage.input_tokens or 0
        output_tokens += usage.output_tokens or 0
        cached_tokens += usage.cached_input_tokens or 0
        if turn.response_id:
            response_ids.append(turn.response_id)
        assistant_message = {
            "role": "assistant",
            "content": turn.content,
            "tool_calls": [
                {"id": call.id, "name": call.name, "arguments": call.arguments} for call in turn.tool_calls
            ],
        }
        messages.append(assistant_message)
        transcript.append(assistant_message)
        trace.add(
            "llm.response",
            "ok",
            duration_ms=(perf_counter() - turn_started) * 1000,
            attributes={"tool_call_count": len(turn.tool_calls)},
            usage={
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cached_input_tokens": usage.cached_input_tokens,
                "reasoning_tokens": None,
                "provider_reported": usage_known,
            },
        )
        if not turn.tool_calls:
            error_category = "agent_protocol"
            break
        for call in turn.tool_calls:
            trace.add("tool.call", "started", attributes={"tool_call_id": call.id, "operation": call.name})
            try:
                outcome = dispatcher.dispatch(call.name, call.arguments)
                result = outcome.output
                status = "ok"
            except Exception as exc:
                result = {"error": str(exc)}
                outcome = None
                status = "error"
                if isinstance(exc, ToolTimeoutError):
                    error_category = "timeout"
                elif isinstance(exc, ToolProtocolError):
                    error_category = "sql_policy" if call.name == "db.execute_readonly" else "agent_protocol"
                else:
                    error_category = "tool_error"
            tool_message = {"role": "tool", "tool_call_id": call.id, "name": call.name, "content": result}
            messages.append(tool_message)
            transcript.append(tool_message)
            duration = outcome.duration_ms if outcome else 0.0
            native_requests.append({"operation": call.name, "status": status, "duration_ms": duration})
            trace.add("tool.result", status, duration_ms=duration, attributes={"tool_call_id": call.id, "operation": call.name})
            if call.name == "db.execute_readonly" and status == "ok":
                trace.add("db.execute", "ok", duration_ms=result["elapsed_ms"], attributes={"result_sha256": result["result_sha256"], "row_count": result["row_count"]})
            if call.name == "benchmark.submit_result" and status == "ok":
                trace.add("answer.submit", "ok", attributes={"status": dispatcher.submission["status"]})
        if dispatcher.submission is not None:
            break

    transcript_path = trial_dir / "conversation.jsonl"
    _jsonl_dump(transcript_path, transcript)
    sql_paths: list[str] = []
    result_paths: list[str] = []
    for index, (handle, result) in enumerate(dispatcher.results.items(), start=1):
        sql_path = trial_dir / "artifacts" / f"candidate-{index:02d}.sql"
        sql_path.parent.mkdir(parents=True, exist_ok=True)
        sql_path.write_text(dispatcher.sql_by_handle[handle].rstrip() + "\n")
        result_path = trial_dir / "artifacts" / f"candidate-{index:02d}.result.json"
        _json_dump(result_path, {"handle": handle, "columns": list(result.columns), "row_count": len(result.rows), "sha256": result_sha256(result)})
        sql_paths.append(_path_ref(sql_path, root_path))
        result_paths.append(_path_ref(result_path, root_path))

    submitted_handles = dispatcher.submission.get("result_handles", []) if dispatcher.submission else []
    candidate_hash = result_sha256(dispatcher.results[submitted_handles[0]]) if submitted_handles else None
    reference_hash: str | None = None
    result_equivalent: bool | None = None
    if dispatcher.submission and dispatcher.submission["status"] == "success" and submitted_handles:
        reference_path = root_path / question["evaluator_only"]["reference_sql"][0]
        reference_sql = reference_path.read_text()
        reference_result = dispatcher.database.execute(reference_sql)
        reference_hash = result_sha256(reference_result)
        result_equivalent = candidate_hash == reference_hash
        error_category = None if result_equivalent else "wrong_result"
    elif dispatcher.submission and dispatcher.submission["status"] == "unsupported":
        error_category = "unsupported_semantics"

    if dispatcher.submission is None:
        status = "timeout" if error_category == "timeout" else "invalid"
        error_category = error_category or "agent_protocol"
    elif dispatcher.submission["status"] == "unsupported":
        status = "unsupported"
    elif dispatcher.submission["status"] == "failed":
        status = "failed"
        error_category = error_category or "agent_protocol"
    else:
        status = "passed" if result_equivalent else "failed"
    trace.add("evaluate.result", "ok" if status == "passed" else "error", attributes={"result_equivalent": result_equivalent})
    trace_status = "ok" if status == "passed" else "unsupported" if status == "unsupported" else "timeout" if status == "timeout" else "error"
    trace.add("trial.end", trace_status, duration_ms=(perf_counter() - started) * 1000, attributes={"status": status})

    return {
        "schema_version": "0.1.0",
        "run_id": trace.run_id,
        "trial_id": trace.trial_id,
        "experiment_id": config["experiment_id"],
        "question": {
            "question_id": question["question_id"],
            "instance_id": question["instance_id"],
            "target_prompt_sha256": _sha256_bytes(question["target_input"]["question"].encode()),
        },
        "condition": {
            "target": target,
            "lane": config["lane"],
            "repetition": int(trace.trial_id.rsplit("-r", 1)[1]),
            "native_surface": target_config["native_surface"]["name"],
            "artifact_sha256": artifact_sha,
            "adapter_version": "control-runner-v0.1",
        },
        "conversation": {
            "fresh": True,
            "system_prompt_sha256": _sha256_bytes(messages[0]["content"].encode()),
            "tool_schema_sha256": _sha256_bytes(json.dumps(tools, sort_keys=True).encode()),
            "sanitized_transcript": _path_ref(transcript_path, root_path),
            "message_count": len(transcript),
            "provider_conversation_id": None,
            "provider_response_ids": response_ids,
        },
        "native_execution": {
            "used_only_declared_surface": all(item["operation"] in dispatcher.allowed_operations for item in native_requests),
            "requests": native_requests,
            "fallback_used": False,
            "unsupported_reason": dispatcher.submission.get("reason") if dispatcher.submission and dispatcher.submission["status"] == "unsupported" else None,
        },
        "candidate": {
            "statement_count": len(submitted_handles),
            "sql_artifacts": sql_paths,
            "result_artifacts": result_paths,
            "answer_artifact": None,
        },
        "evaluation": {
            "execution_success": bool(submitted_handles),
            "result_equivalent": result_equivalent,
            "reference_result_sha256": reference_hash,
            "candidate_result_sha256": candidate_hash,
            "error_category": error_category,
        },
        "usage": {
            "input_tokens": input_tokens if usage_known else None,
            "output_tokens": output_tokens if usage_known else None,
            "cached_input_tokens": cached_tokens if usage_known else None,
            "tool_calls": len(native_requests),
            "database_calls": dispatcher.database_attempts,
            "native_service_calls": 0,
            "total_latency_ms": (perf_counter() - started) * 1000,
            "estimated_cost_usd": None,
            "price_snapshot": None,
        },
        "status": status,
    }
