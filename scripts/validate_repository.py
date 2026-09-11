from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_QUESTION_IDS = [f"q{i:02d}" for i in range(1, 100)]


class ValidationError(RuntimeError):
    pass


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValidationError(f"{path}:{line_no}: expected a JSON object")
        rows.append(value)
    return rows


def validate_serialized_files(root: Path) -> None:
    ignored_parts = {".git", ".venv", "runs", "reports"}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in ignored_parts for part in path.parts):
            continue
        suffix = path.suffix.lower()
        if suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
        elif suffix == ".jsonl":
            _load_jsonl(path)
        elif suffix in {".yaml", ".yml"}:
            yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_canonical_questions(root: Path) -> None:
    path = root / "benchmark/tpcds/questions/canonical/questions.jsonl"
    rows = _load_jsonl(path)
    ids = [row.get("id") for row in rows]
    if ids != EXPECTED_QUESTION_IDS:
        raise ValidationError(
            "canonical questions must contain exactly q01-q99 in order; "
            f"found {len(ids)} rows"
        )

    for row in rows:
        question_id = row["id"]
        reference_sql = row.get("reference_sql", {})
        reference_paths = reference_sql.get("local_files", []) if isinstance(reference_sql, dict) else []
        if not reference_paths:
            raise ValidationError(f"{question_id}: reference_sql.local_files must not be empty")
        for reference in reference_paths:
            candidate = root / reference
            if not candidate.is_file():
                raise ValidationError(f"{question_id}: missing reference SQL: {reference}")


def validate_target_registry(root: Path) -> None:
    registry_path = root / "runner/config/targets.native.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    targets = registry.get("targets", {})
    expected = {"blank_context", "ddl_only", "metricflow", "cube", "ossie", "okf", "skill"}
    if set(targets) != expected:
        raise ValidationError(
            f"native target registry must contain {sorted(expected)}; found {sorted(targets)}"
        )

    for name, config in targets.items():
        allowed = config.get("allowed_operations", [])
        prohibited = config.get("prohibited_operations", [])
        overlap = sorted(set(allowed) & set(prohibited))
        if overlap:
            raise ValidationError(f"{name}: operations are both allowed and prohibited: {overlap}")
        if "benchmark.read_gold" not in prohibited:
            raise ValidationError(f"{name}: benchmark.read_gold must be explicitly prohibited")

        surface = config.get("native_surface", {})
        artifact_root = surface.get("artifact_root")
        if artifact_root is not None and not (root / artifact_root).exists():
            raise ValidationError(f"{name}: missing artifact_root: {artifact_root}")
        tool_catalog = surface.get("tool_catalog")
        if tool_catalog is not None and not (root / tool_catalog).is_file():
            raise ValidationError(f"{name}: missing tool_catalog: {tool_catalog}")


def validate_gold_isolation(root: Path) -> None:
    registry = yaml.safe_load((root / "runner/config/targets.native.yaml").read_text(encoding="utf-8"))
    forbidden_roots = {
        (root / "benchmark/tpcds/results/gold").resolve(),
        (root / "benchmark/tpcds/questions/instances/evaluator-only").resolve(),
    }
    for name, config in registry["targets"].items():
        artifact_root = config.get("native_surface", {}).get("artifact_root")
        if not artifact_root:
            continue
        resolved = (root / artifact_root).resolve()
        for forbidden in forbidden_roots:
            if resolved == forbidden or forbidden in resolved.parents:
                raise ValidationError(f"{name}: native artifact root exposes evaluator-only assets")


def validate_repository(root: Path = ROOT) -> None:
    validate_serialized_files(root)
    validate_canonical_questions(root)
    validate_target_registry(root)
    validate_gold_isolation(root)


def main() -> int:
    try:
        validate_repository(ROOT)
    except Exception as exc:
        print(f"repository validation failed: {exc}")
        return 1
    print("repository validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
