from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
import json
from math import ceil
import os
from pathlib import Path
from statistics import mean, median
import tempfile
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "runner" / "contracts"
STATUSES = ("passed", "failed", "unsupported", "invalid", "timeout", "skipped")
TOKEN_FIELDS = ("input_tokens", "output_tokens", "cached_input_tokens")
CALL_FIELDS = ("tool_calls", "database_calls", "native_service_calls")


class ReportInputError(ValueError):
    """Raised when a report input is invalid or crosses the artifact boundary."""


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((CONTRACTS / name).read_text())


def _validate(instance: Any, schema_name: str, source: Path) -> None:
    validator = Draft202012Validator(_load_schema(schema_name), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.absolute_path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ReportInputError(f"{source}: schema validation failed at {location}: {error.message}")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportInputError(f"Cannot read JSON artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReportInputError(f"Expected a JSON object in {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text().splitlines()
    except OSError as exc:
        raise ReportInputError(f"Cannot read JSONL artifact {path}: {exc}") from exc
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReportInputError(f"Cannot parse {path}:{line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ReportInputError(f"Expected a JSON object at {path}:{line_number}")
        records.append(value)
    if not records:
        raise ReportInputError(f"Trace must contain at least one event: {path}")
    return records


def _inside(path: Path, boundary: Path, label: str) -> Path:
    try:
        path.relative_to(boundary)
    except ValueError as exc:
        raise ReportInputError(f"{label} escapes the artifact root: {path}") from exc
    return path


def _input_path(value: str | Path, artifact_root: Path, label: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = artifact_root / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ReportInputError(f"Cannot resolve {label}: {candidate}") from exc
    return _inside(resolved, artifact_root, label)


def _round(value: float) -> float:
    return round(value, 3)


def _stats(values: Iterable[float]) -> dict[str, int | float | None]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {"count": 0, "min": None, "mean": None, "p50": None, "p95": None, "max": None}
    p95 = ordered[max(0, ceil(0.95 * len(ordered)) - 1)]
    return {
        "count": len(ordered),
        "min": _round(ordered[0]),
        "mean": _round(mean(ordered)),
        "p50": _round(median(ordered)),
        "p95": _round(p95),
        "max": _round(ordered[-1]),
    }


def _coverage(values: Iterable[int | None]) -> dict[str, int]:
    materialized = list(values)
    known = [value for value in materialized if value is not None]
    return {
        "known_trials": len(known),
        "unknown_trials": len(materialized) - len(known),
        "known_total": sum(known),
    }


def _validate_trace(
    trace: list[dict[str, Any]],
    path: Path,
    *,
    run_id: str,
    trial_id: str,
) -> None:
    for event in trace:
        _validate(event, "trace-event.schema.json", path)
    sequences = [event["sequence"] for event in trace]
    if sequences != list(range(len(trace))):
        raise ReportInputError(f"{path}: trace sequences must be contiguous and start at zero")
    if trace[0]["event_type"] != "trial.start" or trace[-1]["event_type"] != "trial.end":
        raise ReportInputError(f"{path}: trace must start with trial.start and end with trial.end")
    for event in trace:
        if event["run_id"] != run_id or event["trial_id"] != trial_id:
            raise ReportInputError(f"{path}: trace identity does not match its trial")
        parent = event.get("parent_sequence")
        if parent is not None and parent >= event["sequence"]:
            raise ReportInputError(f"{path}: parent_sequence must refer to an earlier event")


def _validate_run_summary(run: dict[str, Any], trials: Sequence[dict[str, Any]], source: Path) -> None:
    counts = Counter(trial["status"] for trial in trials)
    summary = run["summary"]
    if summary["planned"] != len(run["trial_records"]):
        raise ReportInputError(f"{source}: summary.planned does not match trial_records")
    if summary["completed"] != sum(counts[status] for status in STATUSES if status != "skipped"):
        raise ReportInputError(f"{source}: summary.completed does not match loaded trials")
    for status in ("passed", "failed", "unsupported", "invalid", "timeout"):
        if summary[status] != counts[status]:
            raise ReportInputError(f"{source}: summary.{status} does not match loaded trials")


def load_validated_artifacts(
    run_path: str | Path,
    *,
    artifact_root: str | Path = ".",
) -> tuple[dict[str, Any], list[dict[str, Any]], list[list[dict[str, Any]]]]:
    """Load only the finalized run, its trial records, and sibling trace streams."""

    root = Path(artifact_root).resolve(strict=True)
    resolved_run = _input_path(run_path, root, "run record")
    if resolved_run.name != "run.json":
        raise ReportInputError("The run record must be named run.json")
    run = _read_json(resolved_run)
    _validate(run, "run-record.schema.json", resolved_run)
    if run["status"] == "running" or run["finished_at"] is None:
        raise ReportInputError(f"{resolved_run}: reports require a finalized run")

    trials_boundary = (resolved_run.parent / "trials").resolve()
    trial_paths: list[Path] = []
    for reference in run["trial_records"]:
        trial_path = _input_path(reference, root, "trial record")
        _inside(trial_path, trials_boundary, "trial record")
        if trial_path.name != "trial.json":
            raise ReportInputError(f"Trial record must be named trial.json: {trial_path}")
        trial_paths.append(trial_path)
    if len(trial_paths) != len(set(trial_paths)):
        raise ReportInputError(f"{resolved_run}: duplicate trial record reference")

    trials: list[dict[str, Any]] = []
    traces: list[list[dict[str, Any]]] = []
    trial_ids: set[str] = set()
    for trial_path in trial_paths:
        trial = _read_json(trial_path)
        _validate(trial, "trial-record.schema.json", trial_path)
        if trial["run_id"] != run["run_id"] or trial["experiment_id"] != run["experiment_id"]:
            raise ReportInputError(f"{trial_path}: trial identity does not match its run")
        if trial["trial_id"] in trial_ids:
            raise ReportInputError(f"{trial_path}: duplicate trial_id {trial['trial_id']}")
        trial_ids.add(trial["trial_id"])

        trace_path = trial_path.with_name("trace.jsonl")
        trace = _read_jsonl(trace_path)
        _validate_trace(trace, trace_path, run_id=run["run_id"], trial_id=trial["trial_id"])
        trials.append(trial)
        traces.append(trace)

    _validate_run_summary(run, trials, resolved_run)
    return run, trials, traces


def build_report(
    run_path: str | Path,
    *,
    artifact_root: str | Path = ".",
) -> dict[str, Any]:
    run, trials, traces = load_validated_artifacts(run_path, artifact_root=artifact_root)
    statuses = Counter(trial["status"] for trial in trials)
    error_categories = Counter(
        trial["evaluation"]["error_category"]
        for trial in trials
        if trial["evaluation"]["error_category"] is not None
    )
    evaluable = statuses["passed"] + statuses["failed"]

    token_usage = {
        field: _coverage(trial["usage"].get(field) for trial in trials) for field in TOKEN_FIELDS
    }
    call_usage = {
        field: _coverage(trial["usage"].get(field) for trial in trials) for field in CALL_FIELDS
    }

    operation_counts: Counter[str] = Counter()
    operation_statuses: dict[str, Counter[str]] = defaultdict(Counter)
    operation_durations: dict[str, list[float]] = defaultdict(list)
    for trial in trials:
        for request in trial["native_execution"]["requests"]:
            operation = request["operation"]
            operation_counts[operation] += 1
            operation_statuses[operation][request["status"]] += 1
            operation_durations[operation].append(request["duration_ms"])

    event_counts: Counter[str] = Counter()
    event_statuses: dict[str, Counter[str]] = defaultdict(Counter)
    event_durations: dict[str, list[float]] = defaultdict(list)
    trace_event_count = 0
    for trace in traces:
        for event in trace:
            event_type = event["event_type"]
            event_counts[event_type] += 1
            event_statuses[event_type][event["status"]] += 1
            trace_event_count += 1
            if event.get("duration_ms") is not None:
                event_durations[event_type].append(event["duration_ms"])

    return {
        "schema_version": "0.1.0",
        "report_type": "offline_run_summary",
        "run": {
            "run_id": run["run_id"],
            "experiment_id": run["experiment_id"],
            "status": run["status"],
            "started_at": run["started_at"],
            "finished_at": run["finished_at"],
            "reproducibility": run["reproducibility"],
        },
        "validation": {
            "all_inputs_valid": True,
            "run_records": 1,
            "trial_records": len(trials),
            "trace_streams": len(traces),
            "trace_events": trace_event_count,
        },
        "outcomes": {
            "total_trials": len(trials),
            "by_status": {status: statuses[status] for status in STATUSES},
            "correctness": {
                "evaluable_trials": evaluable,
                "passed": statuses["passed"],
                "accuracy": _round(statuses["passed"] / evaluable) if evaluable else None,
            },
            "error_categories": dict(sorted(error_categories.items())),
        },
        "usage": {"tokens": token_usage, "calls": call_usage},
        "latency_ms": {
            "trial_total": _stats(trial["usage"]["total_latency_ms"] for trial in trials),
            "by_trace_event": {
                event_type: _stats(event_durations[event_type]) for event_type in sorted(event_counts)
            },
        },
        "native_operations": {
            operation: {
                "count": operation_counts[operation],
                "by_status": dict(sorted(operation_statuses[operation].items())),
                "duration_ms": _stats(operation_durations[operation]),
            }
            for operation in sorted(operation_counts)
        },
        "trace": {
            "by_event_type": {
                event_type: {
                    "count": event_counts[event_type],
                    "by_status": dict(sorted(event_statuses[event_type].items())),
                }
                for event_type in sorted(event_counts)
            }
        },
    }


def _cell(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any], *, language: str = "en") -> str:
    if language not in {"en", "zh-CN"}:
        raise ValueError(f"Unsupported report language: {language}")
    zh = language == "zh-CN"
    run = report["run"]
    outcomes = report["outcomes"]
    correctness = outcomes["correctness"]
    title = "离线 Benchmark 运行报告" if zh else "Offline benchmark run report"
    labels = {
        "run": "运行" if zh else "Run",
        "experiment": "实验" if zh else "Experiment",
        "status": "状态" if zh else "Status",
        "validated": "已验证 Trial" if zh else "Validated trials",
        "outcomes": "结果" if zh else "Outcomes",
        "correctness": "正确性" if zh else "Correctness",
        "errors": "错误分类" if zh else "Error categories",
        "usage": "Token 与调用量" if zh else "Tokens and calls",
        "latency": "延迟（毫秒）" if zh else "Latency (ms)",
        "operations": "原生操作" if zh else "Native operations",
    }
    lines = [
        f"# {title}",
        "",
        f"- {labels['run']}: `{run['run_id']}`",
        f"- {labels['experiment']}: `{run['experiment_id']}`",
        f"- {labels['status']}: `{run['status']}`",
        f"- {labels['validated']}: {report['validation']['trial_records']}",
        "",
        f"## {labels['outcomes']}",
        "",
        "| Status | Count |" if not zh else "| 状态 | 数量 |",
        "| --- | ---: |",
    ]
    lines.extend(f"| `{status}` | {outcomes['by_status'][status]} |" for status in STATUSES)
    accuracy = correctness["accuracy"]
    lines.extend(
        [
            "",
            f"## {labels['correctness']}",
            "",
            (f"Accuracy over evaluable trials: **{_cell(accuracy)}** " if not zh else f"可评测 Trial 的准确率：**{_cell(accuracy)}** ")
            + f"({correctness['passed']}/{correctness['evaluable_trials']}).",
            "",
            f"## {labels['errors']}",
            "",
            "| Category | Count |" if not zh else "| 分类 | 数量 |",
            "| --- | ---: |",
        ]
    )
    if outcomes["error_categories"]:
        lines.extend(f"| `{category}` | {count} |" for category, count in outcomes["error_categories"].items())
    else:
        lines.append("| — | 0 |")

    lines.extend(
        [
            "",
            f"## {labels['usage']}",
            "",
            "| Metric | Known total | Known trials | Unknown trials |"
            if not zh
            else "| 指标 | 已知总量 | 已知 Trial | 未知 Trial |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for group in ("tokens", "calls"):
        for field, coverage in report["usage"][group].items():
            lines.append(
                f"| `{field}` | {coverage['known_total']} | {coverage['known_trials']} | {coverage['unknown_trials']} |"
            )

    trial_latency = report["latency_ms"]["trial_total"]
    lines.extend(
        [
            "",
            f"## {labels['latency']}",
            "",
            "| Scope | Count | Min | Mean | P50 | P95 | Max |"
            if not zh
            else "| 范围 | 数量 | 最小 | 平均 | P50 | P95 | 最大 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            "| `trial_total` | "
            + " | ".join(_cell(trial_latency[key]) for key in ("count", "min", "mean", "p50", "p95", "max"))
            + " |",
        ]
    )
    for event_type, stats in report["latency_ms"]["by_trace_event"].items():
        lines.append(
            f"| `trace:{event_type}` | "
            + " | ".join(_cell(stats[key]) for key in ("count", "min", "mean", "p50", "p95", "max"))
            + " |"
        )

    lines.extend(
        [
            "",
            f"## {labels['operations']}",
            "",
            "| Operation | Count | Statuses | Mean ms | P95 ms |"
            if not zh
            else "| 操作 | 数量 | 状态 | 平均毫秒 | P95 毫秒 |",
            "| --- | ---: | --- | ---: | ---: |",
        ]
    )
    if report["native_operations"]:
        for operation, summary in report["native_operations"].items():
            status_text = ", ".join(f"{key}={value}" for key, value in summary["by_status"].items())
            lines.append(
                f"| `{_cell(operation)}` | {summary['count']} | {_cell(status_text)} | "
                f"{_cell(summary['duration_ms']['mean'])} | {_cell(summary['duration_ms']['p95'])} |"
            )
    else:
        lines.append("| — | 0 | — | — | — |")
    lines.extend(
        [
            "",
            ("P95 uses nearest-rank. Unknown provider usage remains unknown and is never coerced to zero."
             if not zh else "P95 使用 nearest-rank。未知的 Provider 用量保持未知，绝不会被当作零。"),
            "",
        ]
    )
    return "\n".join(lines)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(content)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def generate_report_files(
    run_path: str | Path,
    output_directory: str | Path,
    *,
    artifact_root: str | Path = ".",
    language: str = "en",
    overwrite: bool = False,
) -> tuple[Path, Path]:
    report = build_report(run_path, artifact_root=artifact_root)
    output = Path(output_directory).resolve()
    json_path = output / "report.json"
    markdown_path = output / "report.md"
    existing = [path for path in (json_path, markdown_path) if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(f"Refusing to overwrite report output: {', '.join(map(str, existing))}")
    json_content = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    markdown_content = render_markdown(report, language=language)
    _atomic_write(json_path, json_content)
    _atomic_write(markdown_path, markdown_content)
    return json_path, markdown_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build an offline report from validated benchmark artifacts")
    parser.add_argument("--run", required=True, help="Run-record path, relative to --artifact-root")
    parser.add_argument("--artifact-root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--language", choices=("en", "zh-CN"), default="en")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    json_path, markdown_path = generate_report_files(
        args.run,
        args.output_dir,
        artifact_root=args.artifact_root,
        language=args.language,
        overwrite=args.overwrite,
    )
    print(json_path)
    print(markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
