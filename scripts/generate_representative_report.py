from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from evaluators.execution import EXPECTED_TRIALS, evaluate_execution
from evaluators.structure import evaluate_structure_inventory


ROOT = Path(__file__).resolve().parents[1]


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load_trials(run_dir: Path) -> list[dict[str, Any]]:
    schema = json.loads((ROOT / "runner/contracts/trial-record.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    records: list[dict[str, Any]] = []
    paths = sorted(run_dir.rglob("trial.json"))
    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(record), key=str)
        if errors:
            raise ValueError(f"Invalid trial record {path}: {errors[0].message}")
        records.append(record)
    return records


def _coverage(structure: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for target, counts in structure["status_counts"].items():
        denominator = sum(count for status, count in counts.items() if status != "not_applicable")
        represented = counts["native"] + counts["adapter"] + counts["query_layer"]
        result[target] = {
            "denominator": denominator,
            "represented": represented,
            "unsupported": counts["unsupported"],
            "not_applicable": counts["not_applicable"],
            "coverage": round(represented / denominator, 6) if denominator else None,
        }
    return result


def _render(report: dict[str, Any], *, zh: bool) -> str:
    execution = report["execution"]
    title = "代表性 Benchmark 报告" if zh else "Representative Benchmark Report"
    lines = [f"# {title}", "", "TPC-DS-derived SF1 · representative-v1", ""]
    lines.append("## 执行结果" if zh else "## Execution results")
    lines.append("")
    lines.append("| Target | Accuracy | SQL execution | Completeness | Consistency | p95 ms |" )
    lines.append("|---|---:|---:|---:|---:|---:|")
    for target, row in execution["targets"].items():
        def pct(value: Any) -> str:
            return "n/a" if value is None else f"{100 * value:.1f}%"
        p95 = row["latency_ms"]["p95"]
        lines.append(f"| {target} | {pct(row['execution_accuracy'])} | {pct(row['sql_execution_rate'])} | {pct(row['answer_completeness'])} | {pct(row['three_run_consistency'])} | {p95 if p95 is not None else 'n/a'} |")
    lines += ["", "## 结构保真" if zh else "## Structure fidelity", "", "| Target | Represented / applicable | Unsupported | N/A |", "|---|---:|---:|---:|"]
    for target, row in report["structure_coverage"].items():
        lines.append(f"| {target} | {row['represented']} / {row['denominator']} | {row['unsupported']} | {row['not_applicable']} |")
    lines += ["", "## 配对比较" if zh else "## Paired comparisons", "", "配对比较以问题为单位；q14/q39 的多个 formulation 不增加分母。" if zh else "Paired comparisons use one denominator per question; multiple formulations for q14/q39 do not add denominator weight.", ""]
    lines.append("| Pair | Δ accuracy | 95% CI | p |")
    lines.append("|---|---:|---:|---:|")
    for pair, row in execution["paired_comparisons"].items():
        delta = row["accuracy_delta"]
        ci = row["paired_95pct_ci"]
        p = row["two_sided_sign_test_p"]
        lines.append(f"| {pair} | {delta if delta is not None else 'n/a'} | {ci if ci is not None else 'n/a'} | {p if p is not None else 'n/a'} |")
    lines += ["", "## 边界" if zh else "## Boundaries", ""]
    boundaries = [
        "不生成单一总冠军；结构 coverage 与 Execution Accuracy 分开。" if zh else "No single overall winner is produced; structure coverage is separate from Execution Accuracy.",
        "`not_applicable` 不进入结构分母，`unsupported` 单独保留。" if zh else "`not_applicable` is excluded from structure denominators and `unsupported` remains explicit.",
        "Token 未返回时保持 unavailable，不按零统计。" if zh else "Missing provider token usage remains unavailable rather than being counted as zero.",
        "报告只从冻结 Trial Record 与可审计 Structure Inventory 生成。" if zh else "The report is generated only from frozen Trial Records and the auditable Structure Inventory.",
    ]
    lines.extend(f"- {item}" for item in boundaries)
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the 12x6x3 representative benchmark report")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--structure", type=Path, default=Path("evaluators/structure_inventory.yaml"))
    parser.add_argument("--output", type=Path, default=Path("reports/generated/representative-v1"))
    parser.add_argument("--publication", action="store_true", help="Require the exact 216-trial matrix")
    args = parser.parse_args()

    records = _load_trials(args.run_dir)
    if args.publication and len(records) != EXPECTED_TRIALS:
        raise SystemExit(f"Publication requires exactly {EXPECTED_TRIALS} validated trial records; found {len(records)}")
    execution = evaluate_execution(records, publication=args.publication)
    structure = evaluate_structure_inventory(args.structure, root=ROOT)
    report = {
        "schema_version": "0.1.0",
        "benchmark": "TPC-DS-derived",
        "suite": "representative-v1",
        "source": {
            "trial_count": len(records),
            "structure_inventory": str(args.structure),
            "structure_inventory_sha256": _sha(ROOT / args.structure if not args.structure.is_absolute() else args.structure),
        },
        "execution": execution,
        "structure": structure,
        "structure_coverage": _coverage(structure),
        "global_winner": None,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output / "REPORT.md").write_text(_render(report, zh=False), encoding="utf-8")
    (args.output / "REPORT.zh-CN.md").write_text(_render(report, zh=True), encoding="utf-8")


if __name__ == "__main__":
    main()
