from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from runner.core.control_tools import result_sha256
from runner.core.database import QueryResult
from runner.core.dataset import TPCDS_TABLES, checksum, freeze_gold_result, snapshot_checksum
from runner.core.gold_evaluator import CandidateResultIdentity, FrozenGoldEvaluator, GoldIdentityError


ROOT = Path(__file__).parents[2]


def _snapshot(tmp_path: Path) -> tuple[Path, Path, Path]:
    schema = tmp_path / "schema.sql"
    schema.write_text("\n".join(f'CREATE TABLE "{name}"(id INTEGER);' for name in TPCDS_TABLES))
    database = tmp_path / "sf1.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute(schema.read_text())
        connection.execute("INSERT INTO customer VALUES (1), (2)")
    tables = {}
    for index, name in enumerate(TPCDS_TABLES):
        source = tmp_path / f"{name}.dat"
        source.write_text("1|\n2|\n" if name == "customer" else "")
        tables[name] = {"source": str(source), "rows": 2 if name == "customer" else 0, "sha256": checksum(source)}
    manifest = {
        "schema_version": "0.1.0", "benchmark": "TPC-DS-derived", "scale_factor": 1,
        "generator": {"name": "dsdgen", "version": "4.0.0", "binary_sha256": None},
        "engine": {"name": "duckdb", "version": duckdb.__version__},
        "schema": {"path": str(schema), "sha256": checksum(schema)},
        "database": {"path": str(database), "sha256": checksum(database)},
        "tables": tables, "dataset_sha256": snapshot_checksum(checksum(schema), tables),
        "generated_at": "2026-09-10T00:00:00Z", "elapsed_ms": 1.0,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path, database, schema


def _gold(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    manifest, _, _ = _snapshot(tmp_path)
    reference = tmp_path / "q01.sql"
    reference.write_text("SELECT id AS c_customer_id FROM customer ORDER BY id\n")
    question = {
        "schema_version": "0.1.0", "instance_id": "q01-evaluator-test", "question_id": "q01",
        "source_template": "query1.tpl", "target_input": {"question": "Return IDs."},
        "orchestrator_only": {"parameters": []},
        "evaluator_only": {"reference_sql": [str(reference)], "expected_statement_count": 1,
            "result_contract": {"columns": ["c_customer_id"], "order_sensitive": True,
                "max_rows": 100, "comparison": "exact_normalized"}},
    }
    questions = tmp_path / "questions.jsonl"
    questions.write_text(json.dumps(question) + "\n")
    gold = tmp_path / "q01.json"
    freeze_gold_result(manifest, questions, gold, root=ROOT, publication=False, require_sources=True)
    return gold, manifest, questions, reference


def test_evaluator_compares_identity_without_rows(tmp_path: Path) -> None:
    gold, manifest, questions, reference = _gold(tmp_path)
    evaluator = FrozenGoldEvaluator(gold, manifest_path=manifest, question_instances_path=questions, reference_sql_path=reference, root=tmp_path)
    candidate = CandidateResultIdentity(
        columns=("c_customer_id",), row_count=2,
        sha256=result_sha256(QueryResult(columns=("c_customer_id",), rows=[(1,), (2,)], elapsed_ms=0.0)),
    )
    outcome = evaluator.evaluate(candidate)
    assert outcome.result_equivalent is True
    assert outcome.normalization_revision == "canonical-json-v1"
    assert outcome.duration_ms >= 0
    assert "rows" not in gold.read_text()


def test_evaluator_rejects_identity_or_normalization_mismatch(tmp_path: Path) -> None:
    gold, manifest, questions, reference = _gold(tmp_path)
    evaluator = FrozenGoldEvaluator(gold, manifest_path=manifest, question_instances_path=questions, reference_sql_path=reference, root=tmp_path)
    with pytest.raises(GoldIdentityError, match="normalization"):
        evaluator.evaluate(CandidateResultIdentity(columns=("c_customer_id",), row_count=2, sha256="a" * 64, normalization_revision="other"))
    payload = json.loads(manifest.read_text())
    payload["dataset_sha256"] = "f" * 64
    manifest.write_text(json.dumps(payload))
    with pytest.raises(GoldIdentityError, match="manifest SHA-256"):
        FrozenGoldEvaluator(gold, manifest_path=manifest, question_instances_path=questions, reference_sql_path=reference, root=tmp_path)



def test_evaluator_rejects_gold_with_mismatched_declared_reference_path(tmp_path: Path) -> None:
    gold, manifest, questions, reference = _gold(tmp_path)
    payload = json.loads(gold.read_text())
    payload["reference_sql"]["path"] = str(tmp_path / "other.sql")
    gold.write_text(json.dumps(payload))
    with pytest.raises(GoldIdentityError, match="reference-SQL path"):
        FrozenGoldEvaluator(
            gold,
            manifest_path=manifest,
            question_instances_path=questions,
            reference_sql_path=reference,
            root=tmp_path,
        )
