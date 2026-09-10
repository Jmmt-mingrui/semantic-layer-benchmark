from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from runner.core.dataset import (
    TPCDS_TABLES,
    checksum,
    freeze_gold_result,
    snapshot_checksum,
    validate_sf1_snapshot,
)


ROOT = Path(__file__).parents[2]


def _fixture_snapshot(tmp_path: Path) -> tuple[Path, Path, Path]:
    schema_path = tmp_path / "schema.sql"
    schema_path.write_text(
        "\n".join(f'CREATE TABLE "{name}"(id INTEGER);' for name in TPCDS_TABLES) + "\n"
    )
    database_path = tmp_path / "sf1.duckdb"
    with duckdb.connect(str(database_path)) as database:
        database.execute(schema_path.read_text())
        database.execute("INSERT INTO customer VALUES (2), (1)")

    generated = tmp_path / "generated"
    generated.mkdir()
    tables = {}
    for index, name in enumerate(TPCDS_TABLES):
        source = generated / f"{name}.dat"
        source.write_text("2|\n1|\n" if name == "customer" else "")
        tables[name] = {
            "source": str(source),
            "rows": 2 if name == "customer" else 0,
            "sha256": checksum(source),
        }
    manifest = {
        "schema_version": "0.1.0",
        "benchmark": "TPC-DS-derived",
        "scale_factor": 1,
        "generator": {"name": "dsdgen", "version": "4.0.0", "binary_sha256": None},
        "engine": {"name": "duckdb", "version": duckdb.__version__},
        "schema": {"path": str(schema_path), "sha256": checksum(schema_path)},
        "database": {"path": str(database_path), "sha256": checksum(database_path)},
        "tables": tables,
        "dataset_sha256": snapshot_checksum(checksum(schema_path), tables),
        "generated_at": "2026-09-10T00:00:00Z",
        "elapsed_ms": 1.0,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest) + "\n")
    return manifest_path, schema_path, database_path


def _question_fixture(tmp_path: Path) -> tuple[Path, Path]:
    reference = tmp_path / "q01.sql"
    reference.write_text("SELECT id AS c_customer_id FROM customer ORDER BY id\n")
    question = {
        "schema_version": "0.1.0",
        "instance_id": "q01-freeze-test",
        "question_id": "q01",
        "source_template": "query1.tpl",
        "target_input": {"question": "Return customer IDs in ascending order."},
        "orchestrator_only": {"parameters": []},
        "evaluator_only": {
            "reference_sql": [str(reference)],
            "expected_statement_count": 1,
            "result_contract": {
                "columns": ["c_customer_id"],
                "order_sensitive": True,
                "max_rows": 100,
                "comparison": "exact_normalized",
            },
        },
    }
    questions = tmp_path / "questions.jsonl"
    questions.write_text(json.dumps(question) + "\n")
    return questions, reference


def test_snapshot_preflight_checks_all_tables_and_sources(tmp_path: Path) -> None:
    manifest, _, _ = _fixture_snapshot(tmp_path)
    report = validate_sf1_snapshot(
        manifest, root=ROOT, publication=False, require_sources=True
    )
    assert report["table_count"] == 25
    assert report["total_rows"] == 2
    assert len(report["dataset_sha256"]) == 64


def test_publication_requires_generator_hash_and_relative_paths(tmp_path: Path) -> None:
    manifest, _, _ = _fixture_snapshot(tmp_path)
    with pytest.raises(ValueError, match="binary SHA-256"):
        validate_sf1_snapshot(manifest, root=ROOT, publication=True)


def test_snapshot_preflight_detects_row_count_drift(tmp_path: Path) -> None:
    manifest_path, _, _ = _fixture_snapshot(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    manifest["tables"]["customer"]["rows"] = 3
    manifest["dataset_sha256"] = snapshot_checksum(
        manifest["schema"]["sha256"], manifest["tables"]
    )
    manifest_path.write_text(json.dumps(manifest) + "\n")
    with pytest.raises(ValueError, match="Row count mismatch"):
        validate_sf1_snapshot(manifest_path, root=ROOT, publication=False)


def test_freeze_writes_gold_identity_without_result_rows(tmp_path: Path) -> None:
    manifest, _, _ = _fixture_snapshot(tmp_path)
    questions, reference = _question_fixture(tmp_path)
    output = tmp_path / "q01-gold.json"
    artifact = freeze_gold_result(
        manifest,
        questions,
        output,
        root=ROOT,
        publication=False,
        require_sources=True,
    )
    assert artifact["result"]["columns"] == ["c_customer_id"]
    assert artifact["result"]["row_count"] == 2
    assert len(artifact["result"]["sha256"]) == 64
    assert artifact["reference_sql"]["sha256"] == checksum(reference)
    serialized = output.read_text()
    assert '"rows"' not in serialized
    assert "1, 2" not in serialized
