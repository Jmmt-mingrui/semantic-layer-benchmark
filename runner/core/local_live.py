"""Exploratory live runs with evaluator-only Gold and optional readable details."""
from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shlex
from typing import Any

import yaml

from runner.adapters.metricflow_result import MetricFlowResultAdapter
from runner.core.database import connect, load_database_settings
from runner.core.live_provider import LiveAgentProvider, LiveProviderSettings
from runner.core.native_factory import NativeAdapterFactory, NativeFactorySettings
from runner.core.native_runner import NativeRunnerSettings, run_native_trial
from runner.core.publication_orchestrator import load_gold_for_candidate, materialize_publication_trial
from runner.core.representative_gold import verify_representative_pack


def load_env_file(path: Path) -> None:
    """Read literal dotenv values; never execute shell code or overwrite the environment."""
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:]
        key, separator, value = line.partition("=")
        if not separator or not key.replace("_", "a").isalnum() or key[0].isdigit():
            raise ValueError(f"Invalid dotenv assignment on line {number}")
        parts = shlex.split(value, comments=True)
        if len(parts) > 1:
            raise ValueError(f"Quote dotenv values containing spaces (line {number})")
        os.environ.setdefault(key, parts[0] if parts else "")


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Set {name} in the environment or --env-file")
    return value


def _write_json(path: Path, value: Any, secret: str | None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    if secret:
        text = text.replace(secret, "[REDACTED]")
    path.write_text(text + "\n", encoding="utf-8")


def render_report(rows: list[dict[str, Any]]) -> str:
    lines = ["# 本地探索评测", "", "仅为小规模探索结果，不是完整 216-trial 发布报告。",
        "结果正确性按提交的答案比对冻结 Gold，探索查询不计入答案。", "",
        "| 问题 | 目标 | 运行状态 | Gold 比对 | 耗时（秒） | 工具调用 |",
        "|---|---|---|---|---:|---:|"]
    for row in rows:
        verdict = {True: "正确", False: "不一致", None: "未评分"}[row.get("result_equivalent")]
        status = {"passed": "完成", "failed": "失败", "invalid": "无效", "timeout": "超时",
                  "unsupported": "不支持", "skipped": "跳过"}.get(row["status"], row["status"])
        lines.append(f"| {row['question_id']} | {row['target']} | {status} | {verdict} | "
                     f"{row.get('latency_ms', 0)/1000:.1f} | {row.get('tool_calls', 0)} |")
    for row in rows:
        lines.extend(["", f"## {row['question_id']} / {row['target']}", "", row["question"], ""])
        if row.get("error"):
            lines.extend(["错误：", "", "```text", str(row["error"]), "```", ""])
        details = row.get("details")
        if details is None:
            lines.extend(["未保存查询详情。重新运行时加 `--save-details` 可保存 SQL 和最多 5 行结果预览。", ""])
        else:
            for query in details.get("queries", []):
                lines.extend(["### " + ("提交答案" if query["submitted"] else "探索查询"), "",
                    "```sql", query.get("sql") or "-- 原生引擎未暴露 SQL", "```", "",
                    f"返回 {query['row_count']} 行；以下最多显示 5 行。", "",
                    "```json", json.dumps(query["preview"], ensure_ascii=False, indent=2), "```", ""])
    return "\n".join(lines) + "\n"


def run_local_live(args: Any) -> int:
    root = args.root.resolve()
    if args.env_file:
        load_env_file((root / args.env_file).resolve())
    endpoint = _required("BENCHMARK_AGENT_ENDPOINT").rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint += "/chat/completions"
    provider_settings = LiveProviderSettings(provider=_required("BENCHMARK_AGENT_PROVIDER"),
        model=_required("BENCHMARK_AGENT_MODEL"), endpoint=endpoint,
        api_key_env=os.getenv("BENCHMARK_AGENT_API_KEY_ENV"),
        max_retries=int(os.getenv("BENCHMARK_AGENT_MAX_RETRIES", "0")),
        max_tokens_field=os.getenv("BENCHMARK_AGENT_MAX_TOKENS_FIELD", "max_tokens"))
    secret = provider_settings.resolved_api_key()
    if provider_settings.api_key_env and not secret:
        raise ValueError("The configured credential environment variable is empty")
    instances = root / args.instances
    all_questions = [json.loads(line) for line in instances.read_text().splitlines() if line.strip()]
    selected = {q["question_id"]: q for q in all_questions if q["question_id"] in args.questions}
    if set(selected) != set(args.questions):
        raise ValueError("Requested question not present in materialized instances")
    if args.repetitions < 1 or args.timeout <= 0 or args.max_output_tokens < 1:
        raise ValueError("Repetitions, timeout and output budget must be positive")
    pack_path = root / args.gold_pack
    # This gate is evaluator-owned: no Gold path or reference content enters the target.
    verified = verify_representative_pack(pack_path=pack_path, root=root, publication=True, require_sources=True)
    pack = json.loads(pack_path.read_text())
    if (root / pack["instances_path"]).resolve() != instances.resolve():
        raise ValueError("--instances must be the exact instance file bound by the frozen Gold pack")
    gold_paths = {entry["question_id"]: root / entry["path"] for entry in pack["gold"]}
    settings = NativeRunnerSettings(provider_name=provider_settings.provider, model=provider_settings.model,
        temperature=0, max_output_tokens=args.max_output_tokens, max_turns=args.max_turns,
        provider_timeout_seconds=args.timeout, capture_details=args.save_details)
    registry = yaml.safe_load((root / "runner/config/targets.native.yaml").read_text())
    tools = json.loads((root / "runner/tools/blank-context.tools.json").read_text())
    system_prompt = (root / "runner/prompts/native-agent-system.md").read_text()
    output = (root / args.output).resolve() if args.output else root / "runs" / datetime.now(UTC).strftime("local-live-%Y%m%dT%H%M%S-%f")
    output.mkdir(parents=True, exist_ok=False)
    run_id = output.name
    rows = []
    for repetition in range(1, args.repetitions + 1):
        for target in args.targets:
            for question_id in args.questions:
                question = selected[question_id]
                row = {"question_id": question_id, "question": question["target_input"]["question"],
                       "target": target, "repetition": repetition, "status": "invalid", "result_equivalent": None}
                trial_name = f"{question_id}-{target}-r{repetition:02d}"
                print(f"Running {trial_name} ...", flush=True)
                try:
                    with connect(load_database_settings(root / args.database_config)) as database:
                        factory = NativeAdapterFactory(root=root, registry=registry, database=database, tool_catalog=tools,
                            settings=NativeFactorySettings(metricflow_runtime_project_dir=(root / args.metricflow_runtime).resolve() if args.metricflow_runtime else None,
                                metricflow_executable=args.metricflow_executable,
                                skill_host_revision=args.skill_host_revision or os.getenv("BENCHMARK_SKILL_HOST_REVISION")),
                            adapter_overrides={"metricflow": lambda config, model_root, settings: MetricFlowResultAdapter(
                                target_config=config, model_root=model_root,
                                runtime_project_dir=settings.metricflow_runtime_project_dir, executable=settings.metricflow_executable)})
                        outcome = run_native_trial(target=target, question_instance=question, repetition=repetition,
                            adapter_factory=factory, provider_factory=lambda *unused: LiveAgentProvider(provider_settings),
                            settings=settings, system_prompt=system_prompt, trial_id=trial_name)
                    _write_json(output / (trial_name + ".candidate.json"), outcome.record, secret)
                    gold, _ = load_gold_for_candidate(outcome.record, gold_path=gold_paths[question_id], gold_pack_path=pack_path, root=root)
                    record = materialize_publication_trial(run_id=run_id, experiment_id="representative-v1", lane="native_end_to_end",
                        candidate=outcome.record, native_trace=outcome.trace, gold=gold,
                        output_dir=output, contracts_dir=root / "runner/contracts")
                    row.update(status=record["status"], result_equivalent=record["evaluation"]["result_equivalent"],
                        latency_ms=record["usage"]["total_latency_ms"], tool_calls=record["usage"]["tool_calls"],
                        usage=record["usage"], error=record["evaluation"].get("error_detail"), details=outcome.details)
                    if args.save_details:
                        _write_json(output / (trial_name + ".details.json"), outcome.details, secret)
                except Exception as error:
                    row["error"] = f"{type(error).__name__}: {error}"
                    _write_json(output / (trial_name + ".diagnostic.json"), row, secret)
                rows.append(row)
                _write_json(output / "summary.json", {"publishable": False, "dataset": verified,
                    "provider": provider_settings.provider, "model": provider_settings.model, "trials": rows}, secret)
                report = render_report(rows)
                if secret:
                    report = report.replace(secret, "[REDACTED]")
                (output / "REPORT.zh-CN.md").write_text(report, encoding="utf-8")
                print(f"{trial_name}: {row['status']} / Gold={row['result_equivalent']}", flush=True)
    print(f"Readable report: {output / 'REPORT.zh-CN.md'}")
    return 0 if all(row["status"] == "passed" for row in rows) else 1
