from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.benchmark_lint import (
    ValidationError,
    validate_generated_artifact_hygiene,
    validate_native_registry_invariants,
    validate_readme_pairs,
    validate_target_artifact_isolation,
)


ROOT = Path(__file__).resolve().parents[2]


def _write_registry(root: Path, artifact_root: str) -> None:
    path = root / "runner/config/targets.native.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        yaml.safe_dump(
            {
                "targets": {
                    "example": {
                        "native_surface": {"artifact_root": artifact_root},
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def test_current_native_registry_satisfies_extended_policy() -> None:
    validate_native_registry_invariants(ROOT)
    validate_target_artifact_isolation(ROOT)


def test_readmes_require_english_default_and_chinese_pair(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "README.md").write_text("# English\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="missing Chinese pair"):
        validate_readme_pairs(tmp_path)

    (docs / "README.zh-CN.md").write_text("# 中文\n", encoding="utf-8")
    validate_readme_pairs(tmp_path)


@pytest.mark.parametrize(
    "artifact_root",
    [
        "benchmark/tpcds/results",
        "benchmark/tpcds/results/gold/sf1",
        "benchmark/tpcds/questions/instances",
    ],
)
def test_target_root_cannot_be_above_or_inside_evaluator_assets(
    tmp_path: Path, artifact_root: str
) -> None:
    _write_registry(tmp_path, artifact_root)

    with pytest.raises(ValidationError, match="overlaps evaluator-only assets"):
        validate_target_artifact_isolation(tmp_path)


@pytest.mark.parametrize(
    "relative_path",
    [
        "data/tpcds/sf1/generated/store_sales.dat",
        "data/tpcds/sf1/tpcds.duckdb",
        "runs/run-001.json",
        "reports/generated/report.json",
        "observability/traces/trial.jsonl",
    ],
)
def test_generated_benchmark_artifacts_are_rejected(tmp_path: Path, relative_path: str) -> None:
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("generated", encoding="utf-8")

    with pytest.raises(ValidationError, match="must not be tracked"):
        validate_generated_artifact_hygiene(tmp_path)


def test_gold_identity_rejects_embedded_result_rows(tmp_path: Path) -> None:
    path = tmp_path / "benchmark/tpcds/results/gold/sf1/q01.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"normalized_result": {"rows": [[1]]}}), encoding="utf-8")

    with pytest.raises(ValidationError, match="forbidden result rows"):
        validate_generated_artifact_hygiene(tmp_path)


def test_gold_identity_without_rows_is_allowed(tmp_path: Path) -> None:
    path = tmp_path / "benchmark/tpcds/results/gold/sf1/q01.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "normalized_result": {
                    "columns": ["metric"],
                    "row_count": 1,
                    "sha256": "a" * 64,
                }
            }
        ),
        encoding="utf-8",
    )

    validate_generated_artifact_hygiene(tmp_path)
