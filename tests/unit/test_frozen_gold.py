from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from runner.core.frozen_gold import FrozenGoldError, FrozenGoldEvaluator


ROOT = Path(__file__).parents[2]


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[dict[str, object], Path, Path, list[dict[str, object]], dict[str, str]]:
    manifest = tmp_path / "manifest.json"
    manifest_value = {"dataset_sha256": "d" * 64, "database": {"sha256": "b" * 64}}
    manifest.write_text(json.dumps(manifest_value))
    reference = tmp_path / "reference.sql"
    reference.write_text("not executed by this test\n")
    questions = tmp_path / "questions.jsonl"
    question = {
        "question_id": "q01",
        "instance_id": "q01-test",
        "evaluator_only": {"reference_sql": [str(reference)], "result_contract": {"columns": ["id"], "comparison": "exact_normalized"}},
    }
    questions.write_text(json.dumps(question) + "\n")
    result_hash = sha256(json.dumps({"columns": ["id"], "rows": [[1]]}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps({
        "schema_version": "0.1.0", "benchmark": "TPC-DS-derived", "scale_factor": 1,
        "question_id": "q01", "instance_id": "q01-test",
        "dataset": {"manifest_path": str(manifest), "manifest_sha256": _sha(manifest), "dataset_sha256": "d" * 64, "database_sha256": "b" * 64},
        "question_instance": {"path": str(questions), "sha256": _sha(questions)},
        "reference_sql": {"path": str(reference), "sha256": _sha(reference)},
        "result": {"columns": ["id"], "row_count": 1, "sha256": result_hash, "comparison": "exact_normalized", "order_sensitive": True, "normalization_revision": "canonical-json-v1"},
        "generated_at": "2026-09-10T00:00:00Z",
    }))
    return manifest_value, manifest, questions, [question], {"q01": str(gold)}


def test_frozen_gold_compares_identity_without_rows(tmp_path: Path) -> None:
    manifest_value, manifest, questions, selected, gold_paths = _fixture(tmp_path)
    evaluator = FrozenGoldEvaluator.preflight(root=ROOT, gold_paths=gold_paths, manifest_path=manifest, manifest=manifest_value, questions_path=questions, selected_questions=selected, scale_factor=1)
    result_hash = sha256(json.dumps({"columns": ["id"], "rows": [[1]]}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    evaluation = evaluator.evaluate("q01", columns=["id"], row_count=1, result_sha256=result_hash)
    assert evaluation.result_equivalent is True
    assert evaluation.duration_ms >= 0


def test_frozen_gold_rejects_incomplete_map_before_provider_work(tmp_path: Path) -> None:
    manifest_value, manifest, questions, selected, _ = _fixture(tmp_path)
    with pytest.raises(FrozenGoldError, match="exactly cover"):
        FrozenGoldEvaluator.preflight(root=ROOT, gold_paths={}, manifest_path=manifest, manifest=manifest_value, questions_path=questions, selected_questions=selected, scale_factor=1)
