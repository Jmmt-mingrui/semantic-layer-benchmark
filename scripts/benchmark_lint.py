from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from scripts.validate_repository import (
    ROOT,
    ValidationError,
    validate_canonical_questions,
    validate_serialized_files,
    validate_target_registry,
)


IGNORED_PARTS = {".git", ".venv", ".pytest_cache", "__pycache__"}
FORBIDDEN_SF1_SUFFIXES = {
    ".arrow",
    ".csv",
    ".dat",
    ".db",
    ".duckdb",
    ".feather",
    ".orc",
    ".parquet",
    ".tsv",
    ".wal",
}
RUNTIME_OUTPUT_ROOTS = (
    PurePosixPath("runs"),
    PurePosixPath("reports/generated"),
    PurePosixPath("observability/traces"),
)
EVALUATOR_ONLY_ROOTS = (
    PurePosixPath("benchmark/tpcds/results/gold"),
    PurePosixPath("benchmark/tpcds/questions/instances/evaluator-only"),
)
RAW_RESULT_KEYS = {"rows", "result_rows", "records"}


def _fallback_files(root: Path) -> list[PurePosixPath]:
    return [
        PurePosixPath(path.relative_to(root).as_posix())
        for path in root.rglob("*")
        if path.is_file() and not any(part in IGNORED_PARTS for part in path.relative_to(root).parts)
    ]


def tracked_files(root: Path) -> list[PurePosixPath]:
    """Return repository files, excluding local ignored/generated files when Git is available."""
    try:
        top_level = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        if Path(top_level.stdout.strip()).resolve() != root.resolve():
            return _fallback_files(root)
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return _fallback_files(root)
    return [PurePosixPath(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item]


def _is_within(path: PurePosixPath, parent: PurePosixPath) -> bool:
    return path == parent or parent in path.parents


def _validate_repo_relative(value: Any, *, field: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{field} must be a non-empty repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValidationError(f"{field} must be a normalized repository-relative path: {value}")
    return path


def _overlaps(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _registry(root: Path) -> Mapping[str, Any]:
    value = yaml.safe_load((root / "runner/config/targets.native.yaml").read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValidationError("native target registry must be a YAML mapping")
    return value


def validate_readme_pairs(root: Path) -> None:
    """Require README.md (English default) and README.zh-CN.md to appear together."""
    files = set(tracked_files(root))
    english = {path.parent for path in files if path.name == "README.md"}
    chinese = {path.parent for path in files if path.name == "README.zh-CN.md"}
    missing_chinese = sorted((path / "README.zh-CN.md").as_posix() for path in english - chinese)
    missing_english = sorted((path / "README.md").as_posix() for path in chinese - english)
    if missing_chinese or missing_english:
        details = [*(f"missing Chinese pair: {path}" for path in missing_chinese)]
        details.extend(f"missing English default: {path}" for path in missing_english)
        raise ValidationError("unpaired bilingual README files: " + "; ".join(details))


def validate_native_registry_invariants(root: Path) -> None:
    """Extend the original registry validation with benchmark-wide native-lane policy."""
    validate_target_registry(root)
    registry = _registry(root)
    policy = registry.get("policy")
    common = registry.get("common")
    if not isinstance(policy, Mapping) or not isinstance(common, Mapping):
        raise ValidationError("native target registry requires policy and common mappings")

    required_policy = {
        "primary_lane": "native_end_to_end",
        "preserve_native_artifacts": True,
        "normalize_to_shared_context": False,
        "undeclared_fallback": "forbidden",
    }
    for key, expected in required_policy.items():
        if policy.get(key) != expected:
            raise ValidationError(f"policy.{key} must be {expected!r}")
    if common.get("fresh_conversation_per_trial") is not True:
        raise ValidationError("common.fresh_conversation_per_trial must be true")
    if common.get("raw_gold_access") != "forbidden":
        raise ValidationError("common.raw_gold_access must be forbidden")

    targets = registry.get("targets")
    assert isinstance(targets, Mapping)
    for name, raw_config in targets.items():
        if not isinstance(raw_config, Mapping):
            raise ValidationError(f"{name}: target configuration must be a mapping")
        allowed = raw_config.get("allowed_operations", [])
        prohibited = raw_config.get("prohibited_operations", [])
        for field, operations in (("allowed_operations", allowed), ("prohibited_operations", prohibited)):
            if not isinstance(operations, list) or not all(isinstance(item, str) for item in operations):
                raise ValidationError(f"{name}.{field} must be a list of operation names")
            if len(operations) != len(set(operations)):
                raise ValidationError(f"{name}.{field} contains duplicate operations")
        if common.get("submit_operation") not in allowed:
            raise ValidationError(f"{name}: common submit operation must be allowed")
        if raw_config.get("role") == "executable_semantic_engine" and "db.execute_readonly" not in prohibited:
            raise ValidationError(f"{name}: executable semantic engines must prohibit direct SQL fallback")


def validate_target_artifact_isolation(root: Path) -> None:
    """Reject target-visible roots that are inside or above evaluator-only assets."""
    registry = _registry(root)
    targets = registry.get("targets")
    if not isinstance(targets, Mapping):
        raise ValidationError("native target registry requires a targets mapping")
    repository_root = root.resolve()
    forbidden = [(root / path.as_posix()).resolve() for path in EVALUATOR_ONLY_ROOTS]

    for name, raw_config in targets.items():
        if not isinstance(raw_config, Mapping):
            raise ValidationError(f"{name}: target configuration must be a mapping")
        surface = raw_config.get("native_surface", {})
        if not isinstance(surface, Mapping):
            raise ValidationError(f"{name}.native_surface must be a mapping")
        for field in ("artifact_root", "tool_catalog"):
            value = surface.get(field)
            if value is None:
                continue
            relative = _validate_repo_relative(value, field=f"{name}.native_surface.{field}")
            resolved = (root / relative.as_posix()).resolve()
            if resolved != repository_root and repository_root not in resolved.parents:
                raise ValidationError(f"{name}.{field} escapes the repository: {value}")
            for evaluator_root in forbidden:
                if _overlaps(resolved, evaluator_root):
                    raise ValidationError(
                        f"{name}.{field} overlaps evaluator-only assets: {relative.as_posix()}"
                    )


def _find_raw_result_key(value: Any, path: str = "$") -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in RAW_RESULT_KEYS:
                return child_path
            found = _find_raw_result_key(child, child_path)
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _find_raw_result_key(child, f"{path}[{index}]")
            if found:
                return found
    return None


def validate_generated_artifact_hygiene(root: Path) -> None:
    """Ensure tracked files contain identities and source assets, never generated data/results."""
    for path in tracked_files(root):
        if path.name == ".gitkeep":
            continue
        if _is_within(path, PurePosixPath("data/tpcds/sf1/generated")):
            raise ValidationError(f"generated SF1 source data must not be tracked: {path}")
        if _is_within(path, PurePosixPath("data/tpcds/sf1")) and path.suffix.lower() in FORBIDDEN_SF1_SUFFIXES:
            raise ValidationError(f"generated SF1 database/data must not be tracked: {path}")
        if any(_is_within(path, output_root) for output_root in RUNTIME_OUTPUT_ROOTS):
            raise ValidationError(f"runtime output must not be tracked: {path}")

        gold_root = PurePosixPath("benchmark/tpcds/results/gold")
        if not _is_within(path, gold_root) or path.name in {"README.md", "README.zh-CN.md"}:
            continue
        if path.suffix.lower() != ".json":
            raise ValidationError(f"Gold artifacts may only contain JSON identities: {path}")
        value = json.loads((root / path.as_posix()).read_text(encoding="utf-8"))
        raw_key = _find_raw_result_key(value)
        if raw_key:
            raise ValidationError(f"Gold identity contains forbidden result rows at {path}:{raw_key}")


CHECKS: Mapping[str, Callable[[Path], None]] = {
    "serialized-assets": validate_serialized_files,
    "canonical-questions": validate_canonical_questions,
    "readme-pairs": validate_readme_pairs,
    "native-registry": validate_native_registry_invariants,
    "target-isolation": validate_target_artifact_isolation,
    "artifact-hygiene": validate_generated_artifact_hygiene,
}


def validate_benchmark_invariants(root: Path = ROOT, checks: Iterable[str] | None = None) -> None:
    selected = list(checks) if checks is not None else list(CHECKS)
    for name in selected:
        try:
            check = CHECKS[name]
        except KeyError as exc:
            raise ValidationError(f"unknown lint check: {name}") from exc
        check(root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate semantic-layer benchmark repository invariants.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root (defaults to this checkout).")
    parser.add_argument(
        "--check",
        action="append",
        choices=sorted(CHECKS),
        help="Run only this check; repeat the option to select multiple checks.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    selected = args.check or list(CHECKS)
    try:
        for name in selected:
            CHECKS[name](root)
            print(f"PASS {name}")
    except Exception as exc:
        print(f"FAIL {name}: {exc}", file=sys.stderr)
        return 1
    print(f"benchmark lint passed ({len(selected)} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
