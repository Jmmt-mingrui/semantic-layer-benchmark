from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

import yaml


ALLOWED_STATUSES = frozenset({"native", "adapter", "query_layer", "unsupported", "not_applicable"})
EXPECTED_CATEGORIES = (
    "dataset_field",
    "dimension",
    "entity_relationship",
    "role_playing_join",
    "fact_grain",
    "metric_base",
    "metric_derived",
    "metric_ratio",
    "metric_cumulative",
    "time_role",
    "additivity_semi_additivity",
    "null_divide_by_zero",
    "provenance",
    "native_validation",
)
EXPECTED_TARGETS = ("blank_context", "ddl_only", "metricflow", "ossie", "okf", "skill")


class StructureEvaluationError(RuntimeError):
    pass


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _hash_tree(root: Path) -> str:
    if root.is_file():
        return _hash_file(root)
    files = sorted(path for path in root.rglob("*") if path.is_file())
    payload = [f"{path.relative_to(root).as_posix()}:{_hash_file(path)}" for path in files]
    return sha256("\n".join(payload).encode("utf-8")).hexdigest()


def evaluate_structure_inventory(path: str | Path, *, root: str | Path = ".") -> dict[str, Any]:
    """Validate the auditable structure inventory without producing a global score."""

    root_path = Path(root).resolve()
    inventory_path = Path(path)
    if not inventory_path.is_absolute():
        inventory_path = root_path / inventory_path
    document = yaml.safe_load(inventory_path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise StructureEvaluationError("Structure inventory must be a mapping")
    if document.get("benchmark") != "TPC-DS-derived":
        raise StructureEvaluationError("Structure inventory must identify TPC-DS-derived")
    if tuple(document.get("categories", ())) != EXPECTED_CATEGORIES:
        raise StructureEvaluationError("Structure categories differ from the benchmark contract")
    if set(document.get("allowed_statuses", ())) != ALLOWED_STATUSES:
        raise StructureEvaluationError("Structure inventory status vocabulary is invalid")
    targets = document.get("targets")
    if not isinstance(targets, Mapping) or tuple(targets) != EXPECTED_TARGETS:
        raise StructureEvaluationError("Structure inventory must contain the six targets in canonical order")

    rows: list[dict[str, Any]] = []
    summary: dict[str, dict[str, int]] = {}
    for target in EXPECTED_TARGETS:
        target_values = targets[target]
        if not isinstance(target_values, Mapping) or set(target_values) != set(EXPECTED_CATEGORIES):
            raise StructureEvaluationError(f"{target}: structure categories are incomplete")
        summary[target] = {status: 0 for status in sorted(ALLOWED_STATUSES)}
        for category in EXPECTED_CATEGORIES:
            entry = target_values[category]
            if not isinstance(entry, Mapping):
                raise StructureEvaluationError(f"{target}.{category}: entry must be a mapping")
            status = entry.get("status")
            if status not in ALLOWED_STATUSES:
                raise StructureEvaluationError(f"{target}.{category}: invalid status {status!r}")
            evidence = entry.get("evidence")
            if not isinstance(evidence, str) or not evidence:
                raise StructureEvaluationError(f"{target}.{category}: evidence path is required")
            evidence_path = (root_path / evidence).resolve()
            if not evidence_path.is_relative_to(root_path) or not evidence_path.exists():
                raise StructureEvaluationError(f"{target}.{category}: evidence path is missing or escapes the repo")
            summary[target][str(status)] += 1
            rows.append(
                {
                    "target": target,
                    "category": category,
                    "status": status,
                    "evidence": evidence,
                    "evidence_sha256": _hash_tree(evidence_path),
                    "note": entry.get("note"),
                }
            )

    # No weighted or aggregate quality score is produced. not_applicable remains
    # visible and is excluded only from optional coverage denominators in reports.
    return {
        "schema_version": "0.1.0",
        "benchmark": "TPC-DS-derived",
        "inventory_path": inventory_path.relative_to(root_path).as_posix(),
        "inventory_sha256": _hash_file(inventory_path),
        "categories": list(EXPECTED_CATEGORIES),
        "targets": list(EXPECTED_TARGETS),
        "rows": rows,
        "status_counts": summary,
    }


def write_structure_evaluation(result: Mapping[str, Any], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output
