"""Unified fresh-session runner for native semantic targets.

This runner deliberately stops at candidate production.  It has no Gold path,
reference SQL path, question-to-metric map, or evaluator dependency.  Gold is
loaded by a later evaluator only after this runtime and provider are closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence
from uuid import uuid4

from runner.core.agent import AgentProvider, AgentUsage, ToolCall
from runner.core.native_adapter import NativeIsolationError, NativeOperationError, NativeRequest, TargetQuestion
from runner.core.native_factory import NativeAdapterFactory, SUPPORTED_TARGETS


class NativeRunnerError(RuntimeError):
    pass


class _PreflightFailure(RuntimeError):
    """Internal control-flow signal used so finalization happens after close()."""


ProviderFactory = Callable[[str, int, Mapping[str, str]], AgentProvider]
TokenValue = int | str


@dataclass(frozen=True)
class NativeRunnerSettings:
    provider_name: str
    model: str
    temperature: float
    max_output_tokens: int
    max_turns: int = 12
    provider_timeout_seconds: float = 120
    tool_timeout_seconds: float = 60
    seed: int | None = None
    parallel_tool_calls: bool = False

    def generation(self) -> dict[str, Any]:
        return {
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "seed": self.seed,
            "parallel_tool_calls": self.parallel_tool_calls,
        }


@dataclass(frozen=True)
class NativeTrialArtifacts:
    record: dict[str, Any]
    trace: tuple[dict[str, Any], ...]


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _hash_json(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _assistant_message(content: str | None, calls: Sequence[ToolCall]) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if calls:
        message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": json.dumps(call.arguments, ensure_ascii=False, separators=(",", ":")),
                },
            }
            for call in calls
        ]
    return message


def _token_summary(usages: Sequence[AgentUsage], field: str) -> TokenValue:
    # Never undercount provider usage.  If even one turn omits a token field,
    # the trial-level value is explicitly unavailable rather than zero or a
    # partial sum.
    values = [getattr(usage, field) for usage in usages]
    if not values or any(value is None for value in values):
        return "unavailable"
    return sum(int(value) for value in values if value is not None)


def _response_status(status: str) -> str:
    if status in {"ok", "succeeded"}:
        return "ok"
    if status == "unsupported":
        return "unsupported"
    if status == "timeout":
        return "timeout"
    return "error"


def _trace_event(
    sequence: int,
    event_type: str,
    status: str,
    *,
    duration_ms: float | None = None,
    attributes: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "sequence": sequence,
        "event_type": event_type,
        "status": status,
        "attributes": dict(attributes or {}),
    }
    if duration_ms is not None:
        event["duration_ms"] = round(float(duration_ms), 3)
    return event


def run_native_trial(
    *,
    target: str,
    question_instance: Mapping[str, Any],
    repetition: int,
    adapter_factory: NativeAdapterFactory,
    provider_factory: ProviderFactory,
    settings: NativeRunnerSettings,
    system_prompt: str,
    user_prompt_template: str = "{{question}}",
    trial_id: str | None = None,
) -> NativeTrialArtifacts:
    """Run exactly one fresh ``question × target × repetition`` trial."""

    if target not in SUPPORTED_TARGETS:
        raise NativeRunnerError(f"Unsupported native target: {target}")
    if repetition < 1:
        raise NativeRunnerError("repetition must be positive")
    if user_prompt_template.count("{{question}}") != 1:
        raise NativeRunnerError("user_prompt_template must contain {{question}} exactly once")
    question = TargetQuestion.from_instance(dict(question_instance))
    trial_id = trial_id or f"{question.instance_id}-{target}-r{repetition:02d}-{uuid4().hex[:8]}"
    trace: list[dict[str, Any]] = []
    started = perf_counter()
    runtime = adapter_factory.create(target)
    provider: AgentProvider | None = None
    messages: list[dict[str, Any]] = []
    usages: list[AgentUsage] = []
    response_ids: list[str] = []
    native_requests: list[dict[str, Any]] = []
    tool_call_count = 0
    error_category: str | None = None
    error_detail: str | None = None
    completion_status = "invalid"
    provider_closed = False
    tools: Sequence[dict[str, Any]] = ()
    tool_schema_sha256 = _hash_json([])

    def add_event(event_type: str, status: str, **kwargs: Any) -> None:
        trace.append(_trace_event(len(trace), event_type, status, **kwargs))

    try:
        add_event("trial.start", "started", attributes={"target": target, "repetition": repetition})

        # Capture the declared tool surface while the runtime is open.  The
        # identity is immutable for the trial and must not depend on close().
        tools = tuple(runtime.public_tools())
        tool_schema_sha256 = _hash_json(tools)

        preflight_started = perf_counter()
        preflight = runtime.preflight(settings.tool_timeout_seconds)
        preflight_ms = (perf_counter() - preflight_started) * 1000
        for response in preflight:
            native_requests.append(
                {
                    "operation": response.output.get("native_operation", "preflight"),
                    "status": _response_status(response.status),
                    "duration_ms": round(response.duration_ms, 3),
                    "request_artifact": response.request_artifact,
                    "response_artifact": response.response_artifact,
                }
            )
        if any(_response_status(response.status) not in {"ok"} for response in preflight):
            completion_status = "failed"
            error_category = "preflight"
            error_detail = "native preflight did not succeed"
            add_event("target.preflight", "error", duration_ms=preflight_ms)
            raise _PreflightFailure(error_detail)
        add_event("target.preflight", "ok", duration_ms=preflight_ms, attributes={"checks": len(preflight)})

        # Conversation is constructed here, after preflight, from scratch.  No
        # object from another trial is accepted as input.
        messages = [{"role": "system", "content": system_prompt}]
        if runtime.initial_context:
            messages.append({"role": "system", "content": runtime.initial_context})
            add_event(
                "context.initial",
                "ok",
                attributes={"sha256": _hash_text(runtime.initial_context), "target": target},
            )
        rendered_question = user_prompt_template.replace("{{question}}", question.prompt)
        messages.append({"role": "user", "content": rendered_question})
        tool_names = [str(tool["name"]) for tool in tools]
        declared = set(runtime.target_config.get("allowed_operations", ()))
        if not set(tool_names).issubset(declared):
            raise NativeRunnerError("runtime exposed an operation outside the target allowlist")
        if "benchmark.read_gold" in tool_names:
            raise NativeIsolationError("Gold operation must never be exposed to an Agent")
        if target == "metricflow" and any(name.startswith("db.") for name in tool_names):
            raise NativeIsolationError("MetricFlow target must not expose direct database SQL tools")
        add_event("conversation.start", "ok", attributes={"fresh": True, "tool_names": tool_names})

        # New provider object is constructed only after the fresh message list is
        # complete.  The matrix runner additionally proves objects are not reused.
        provider = provider_factory(target, repetition, question.provider_context())
        if not hasattr(provider, "complete"):
            raise NativeRunnerError("provider_factory must return an AgentProvider")

        for turn_index in range(settings.max_turns):
            provider_started = perf_counter()
            turn = provider.complete(
                tuple(messages),
                tools,
                settings.generation(),
                settings.provider_timeout_seconds,
            )
            provider_ms = (perf_counter() - provider_started) * 1000
            usages.append(turn.usage)
            if turn.response_id:
                response_ids.append(turn.response_id)
            add_event(
                "llm.generate",
                "ok",
                duration_ms=provider_ms,
                attributes={
                    "turn": turn_index + 1,
                    "tool_call_count": len(turn.tool_calls),
                    # No chain-of-thought, reasoning tokens, or inferred reasoning
                    # content is requested or recorded.
                },
            )
            messages.append(_assistant_message(turn.content, turn.tool_calls))

            if not turn.tool_calls:
                if runtime.submission is not None:
                    break
                error_category = "agent_protocol"
                error_detail = "Agent returned no tool call before benchmark.submit_result"
                completion_status = "failed"
                break

            for call in turn.tool_calls:
                tool_call_count += 1
                tool_started = perf_counter()
                try:
                    response = runtime.dispatch(
                        NativeRequest(
                            operation=call.name,
                            arguments=dict(call.arguments),
                            deadline_seconds=settings.tool_timeout_seconds,
                        )
                    )
                    duration_ms = (perf_counter() - tool_started) * 1000
                    status = _response_status(response.status)
                    native_requests.append(
                        {
                            "operation": call.name,
                            "status": status,
                            "duration_ms": round(response.duration_ms, 3),
                            "request_artifact": response.request_artifact,
                            "response_artifact": response.response_artifact,
                        }
                    )
                    add_event(
                        "tool.call",
                        status,
                        duration_ms=duration_ms,
                        attributes={"operation": call.name, "call_id": call.id},
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": call.name,
                            "content": json.dumps(response.output, ensure_ascii=False, separators=(",", ":")),
                        }
                    )
                    if status == "unsupported":
                        # Native unsupported is visible to the Agent; it may choose
                        # a different native request or submit unsupported.
                        continue
                except (NativeIsolationError, NativeOperationError) as error:
                    error_category = "protocol_violation"
                    error_detail = str(error)
                    completion_status = "invalid"
                    add_event("tool.call", "error", attributes={"operation": call.name, "category": error_category})
                    raise
                except Exception as error:  # native/tool errors are repairable within budget
                    duration_ms = (perf_counter() - tool_started) * 1000
                    native_requests.append(
                        {
                            "operation": call.name,
                            "status": "error",
                            "duration_ms": round(duration_ms, 3),
                            "request_artifact": None,
                            "response_artifact": None,
                        }
                    )
                    add_event(
                        "tool.call",
                        "error",
                        duration_ms=duration_ms,
                        attributes={"operation": call.name, "error_type": error.__class__.__name__},
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": call.name,
                            "content": json.dumps(
                                {"status": "error", "error_type": error.__class__.__name__, "message": str(error)[:500]},
                                ensure_ascii=False,
                            ),
                        }
                    )
                if runtime.submission is not None:
                    break
            if runtime.submission is not None:
                break
        else:
            completion_status = "timeout"
            error_category = "turn_budget"
            error_detail = "Agent exhausted max_turns without final submission"

        if runtime.submission is not None:
            submitted = runtime.submission
            if submitted.get("status") == "success":
                completion_status = "candidate_ready"
            elif submitted.get("status") == "unsupported":
                completion_status = "unsupported"
                error_category = "unsupported_semantics"
                error_detail = str(submitted.get("reason") or "native surface reported unsupported")
            else:
                completion_status = "failed"
                error_category = "agent_reported_failure"
                error_detail = str(submitted.get("reason") or "Agent reported failure")

    except _PreflightFailure:
        # State is already recorded above; continue through finally so lifecycle
        # closure is reflected in the returned record.
        pass
    except (NativeIsolationError, NativeOperationError):
        if error_category is None:
            error_category = "protocol_violation"
        if error_detail is None:
            error_detail = "undeclared or evaluator-only operation attempted"
        completion_status = "invalid"
    except TimeoutError as error:
        error_category = "timeout"
        error_detail = str(error)
        completion_status = "timeout"
    except Exception as error:
        error_category = error_category or "internal"
        error_detail = error_detail or f"{error.__class__.__name__}: {str(error)[:500]}"
        completion_status = "failed"
    finally:
        # The target and provider are closed before any caller may evaluate Gold.
        runtime.close()
        if provider is not None:
            close = getattr(provider, "close", None)
            if callable(close):
                close()
        provider_closed = True
        add_event("conversation.close", "ok", attributes={"provider_closed": provider_closed})

    return _finalize(
        trial_id,
        target,
        repetition,
        question,
        runtime,
        provider,
        settings,
        system_prompt,
        tool_schema_sha256,
        messages,
        usages,
        response_ids,
        native_requests,
        tool_call_count,
        completion_status,
        error_category,
        error_detail,
        started,
        trace,
        provider_closed,
    )


def _finalize(
    trial_id: str,
    target: str,
    repetition: int,
    question: TargetQuestion,
    runtime: Any,
    provider: AgentProvider | None,
    settings: NativeRunnerSettings,
    system_prompt: str,
    tool_schema_sha256: str,
    messages: Sequence[Mapping[str, Any]],
    usages: Sequence[AgentUsage],
    response_ids: Sequence[str],
    native_requests: Sequence[Mapping[str, Any]],
    tool_call_count: int,
    completion_status: str,
    error_category: str | None,
    error_detail: str | None,
    started: float,
    trace: list[dict[str, Any]],
    provider_closed: bool,
) -> NativeTrialArtifacts:
    total_latency_ms = (perf_counter() - started) * 1000
    provider_kind = str(getattr(provider, "provider_kind", "unavailable")) if provider is not None else "unavailable"
    ranking_eligible = bool(getattr(provider, "ranking_eligible", False)) if provider is not None else False
    retries = int(getattr(provider, "retry_count", 0)) if provider is not None else 0
    sql_hashes = [
        {"result_handle": handle, "sql_sha256": _hash_text(sql)}
        for handle, sql in runtime.sql_by_handle.items()
    ]
    result_hashes = []
    for handle, result in runtime.results.items():
        from runner.core.control_tools import result_sha256

        result_hashes.append({"result_handle": handle, "result_sha256": result_sha256(result)})

    # Persist only hashes and role/tool metadata, not full prompts, tool outputs,
    # raw rows, secrets, or hidden reasoning.
    message_manifest = [
        {
            "role": message.get("role"),
            "name": message.get("name"),
            "tool_call_id": message.get("tool_call_id"),
            "content_sha256": _hash_text(str(message.get("content"))) if message.get("content") is not None else None,
        }
        for message in messages
    ]
    record = {
        "schema_version": "0.2.0",
        "trial_id": trial_id,
        "question": {
            "question_id": question.question_id,
            "instance_id": question.instance_id,
            "question_sha256": _hash_text(question.prompt),
        },
        "condition": {
            "target": target,
            "repetition": repetition,
            "native_surface": runtime.target_config.get("native_surface", {}).get("name"),
            "artifact_sha256": runtime.artifact_sha256,
            "adapter_version": runtime.adapter_version,
        },
        "conversation": {
            "fresh": True,
            "provider_closed_before_evaluation": provider_closed,
            "system_prompt_sha256": _hash_text(system_prompt),
            "tool_schema_sha256": tool_schema_sha256,
            "message_manifest": message_manifest,
            "message_count": len(messages),
            "provider_response_ids": list(response_ids),
        },
        "provider": {
            "configured_provider": settings.provider_name,
            "model": settings.model,
            "kind": provider_kind,
            "ranking_eligible": ranking_eligible,
            "temperature": settings.temperature,
            "max_output_tokens": settings.max_output_tokens,
            "timeout_seconds": settings.provider_timeout_seconds,
            "retries": retries,
        },
        "native_execution": {
            "used_only_declared_surface": error_category != "protocol_violation",
            "requests": list(native_requests),
            "fallback_used": False,
        },
        "candidate": {
            "submission": runtime.submission,
            "sql_artifacts": sql_hashes,
            "result_artifacts": result_hashes,
        },
        "usage": {
            "input_tokens": _token_summary(usages, "input_tokens"),
            "output_tokens": _token_summary(usages, "output_tokens"),
            "cached_input_tokens": _token_summary(usages, "cached_input_tokens"),
            "tool_calls": tool_call_count,
            "database_calls": runtime.database_calls,
            "total_latency_ms": round(total_latency_ms, 3),
            "retries": retries,
        },
        "error": {
            "category": error_category,
            "detail": error_detail,
        },
        "status": completion_status,
    }
    trace.append(
        _trace_event(
            len(trace),
            "trial.finish",
            "ok" if completion_status == "candidate_ready" else completion_status,
            duration_ms=total_latency_ms,
            attributes={"status": completion_status},
        )
    )
    return NativeTrialArtifacts(record=record, trace=tuple(trace))


def run_native_matrix(
    *,
    targets: Sequence[str],
    questions: Sequence[Mapping[str, Any]],
    repetitions: int,
    adapter_factory: NativeAdapterFactory,
    provider_factory: ProviderFactory,
    settings: NativeRunnerSettings,
    system_prompt: str,
    user_prompt_template: str = "{{question}}",
) -> tuple[NativeTrialArtifacts, ...]:
    """Run a matrix while proving provider objects are never reused across trials."""

    if repetitions < 1:
        raise NativeRunnerError("repetitions must be positive")
    provider_ids: set[int] = set()
    provider_refs: list[AgentProvider] = []

    def fresh_provider(target: str, repetition: int, context: Mapping[str, str]) -> AgentProvider:
        provider = provider_factory(target, repetition, context)
        identity = id(provider)
        if identity in provider_ids:
            raise NativeRunnerError("provider_factory reused a provider instance across trials")
        provider_ids.add(identity)
        provider_refs.append(provider)  # prevent CPython id reuse during this matrix
        return provider

    outcomes: list[NativeTrialArtifacts] = []
    for repetition in range(1, repetitions + 1):
        for target in targets:
            for question in questions:
                outcomes.append(
                    run_native_trial(
                        target=target,
                        question_instance=question,
                        repetition=repetition,
                        adapter_factory=adapter_factory,
                        provider_factory=fresh_provider,
                        settings=settings,
                        system_prompt=system_prompt,
                        user_prompt_template=user_prompt_template,
                    )
                )
    return tuple(outcomes)


def write_native_run(directory: str | Path, outcomes: Sequence[NativeTrialArtifacts]) -> Path:
    """Persist sanitized trial/trace JSONL without Gold or raw result rows."""

    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    trials_path = root / "trials.jsonl"
    traces_path = root / "traces.jsonl"
    trials_path.write_text(
        "".join(json.dumps(item.record, ensure_ascii=False, sort_keys=True) + "\n" for item in outcomes),
        encoding="utf-8",
    )
    traces_path.write_text(
        "".join(
            json.dumps({"trial_id": item.record["trial_id"], **event}, ensure_ascii=False, sort_keys=True) + "\n"
            for item in outcomes
            for event in item.trace
        ),
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "0.2.0",
        "trial_count": len(outcomes),
        "ranking_eligible_trial_count": sum(bool(item.record["provider"]["ranking_eligible"]) for item in outcomes),
        "scripted_trial_count": sum(item.record["provider"]["kind"] == "scripted" for item in outcomes),
        "trials_sha256": sha256(trials_path.read_bytes()).hexdigest(),
        "traces_sha256": sha256(traces_path.read_bytes()).hexdigest(),
    }
    manifest_path = root / "run-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path
