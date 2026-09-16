from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path

import pytest

from runner.core.database import QueryResult
from runner.core.question_contracts import render_output_requirements
from runner.core.representative_gold import (
    REPRESENTATIVE_QUESTION_IDS,
    RepresentativeGoldError,
    freeze_representative_pack,
    load_representative_instances,
    verify_representative_pack,
)


ROOT = Path(__file__).resolve().parents[2]
INSTANCES = ROOT / "benchmark/tpcds/questions/instances/sf1-representative-v1.jsonl"


def test_checked_in_representative_instances_are_exactly_the_selected_twelve() -> None:
    rows = load_representative_instances(INSTANCES)
    assert tuple(row["question_id"] for row in rows) == REPRESENTATIVE_QUESTION_IDS
    assert len(rows) == 12
    assert all(row["benchmark"] == "TPC-DS-derived" for row in rows)
    assert len(next(row for row in rows if row["question_id"] == "q14")["evaluator_only"]["reference_sql"]) == 2
    assert len(next(row for row in rows if row["question_id"] == "q39")["evaluator_only"]["reference_sql"]) == 2


def _write_fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "benchmark": "TPC-DS-derived",
                "scale_factor": 1,
                "dataset_sha256": "d" * 64,
                "generator": {"name": "dsdgen", "version": "4.0.0", "binary_sha256": "b" * 64},
                "engine": {"name": "duckdb", "version": "1.4.0"},
                "database": {"sha256": "e" * 64},
            }
        ),
        encoding="utf-8",
    )
    sql_paths: dict[str, str] = {}
    rows = []
    for question_id in REPRESENTATIVE_QUESTION_IDS:
        count = 2 if question_id in {"q14", "q39"} else 1
        refs = []
        for statement in range(1, count + 1):
            path = tmp_path / f"{question_id}-{statement}.sql"
            path.write_text(f"select '{question_id}-{statement}' as value order by value\n", encoding="utf-8")
            refs.append(str(path))
            sql_paths[f"{question_id}-{statement}"] = str(path)
        contract = {"columns": ["value"], "order_sensitive": True, "max_rows": None,
                    "comparison": "exact_normalized", "order_by": [{"column": "value", "direction": "ASC", "nulls": "LAST"}]}
        contracts = [contract for _ in range(count)]
        rows.append(
            {
                "schema_version": "0.3.0",
                "suite": "representative-v1",
                "benchmark": "TPC-DS-derived",
                "scale_factor": 1,
                "question_id": question_id,
                "instance_id": f"{question_id}-fixture",
                "source_template": f"query{int(question_id[1:])}.tpl",
                "target_input": {"question": f"fixture {question_id} " + render_output_requirements(contracts)},
                "orchestrator_only": {"parameters": []},
                "evaluator_only": {"reference_sql": refs, "expected_statement_count": count,
                    "result_contract": contract if count == 1 else {"statements": contracts},
                    "provenance": {"canonical_question": "fixture", "reference_source": "fixture",
                                   "materialization_revision": "public-output-contract-v1"}},
            }
        )
    instances = tmp_path / "instances.jsonl"
    instances.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return manifest, instances, sql_paths


def test_freeze_writes_only_result_identities_and_verification_fails_on_sql_change(tmp_path: Path, monkeypatch) -> None:
    manifest, instances, sql_paths = _write_fixture(tmp_path)
    manifest_sha = sha256(manifest.read_bytes()).hexdigest()

    def fake_snapshot(*args, **kwargs):
        del args, kwargs
        return {
            "manifest_path": manifest,
            "manifest_sha256": manifest_sha,
            "dataset_sha256": "d" * 64,
            "database_sha256": "e" * 64,
            "database_path": tmp_path / "fake.duckdb",
            "table_count": 24,
            "total_rows": 1,
        }

    class FakeDatabase:
        def execute(self, sql):
            marker = sql.strip().split("'")[1]
            return QueryResult(columns=("value",), rows=((f"secret-row-{marker}",),), elapsed_ms=1.0)

    @contextmanager
    def fake_connect(settings):
        del settings
        yield FakeDatabase()

    monkeypatch.setattr("runner.core.representative_gold.validate_sf1_snapshot", fake_snapshot)
    monkeypatch.setattr("runner.core.representative_gold.connect", fake_connect)

    output = tmp_path / "gold"
    first_pack = freeze_representative_pack(
        manifest_path=manifest,
        instances_path=instances,
        output_dir=output,
        root=ROOT,
        publication=False,
        require_sources=False,
    )
    assert first_pack["question_count"] == 12
    assert first_pack["statement_count"] == 14
    assert all(entry["identity_sha256"] for entry in first_pack["gold"])
    for question_id in REPRESENTATIVE_QUESTION_IDS:
        text = (output / f"{question_id}.json").read_text(encoding="utf-8")
        assert "secret-row" not in text
        document = json.loads(text)
        assert all("rows" not in statement["result"] for statement in document["statements"])

    second_pack = freeze_representative_pack(
        manifest_path=manifest,
        instances_path=instances,
        output_dir=output,
        root=ROOT,
        publication=False,
        require_sources=False,
    )
    assert second_pack["pack_identity_sha256"] == first_pack["pack_identity_sha256"]
    assert [entry["identity_sha256"] for entry in second_pack["gold"]] == [
        entry["identity_sha256"] for entry in first_pack["gold"]
    ]

    verified = verify_representative_pack(
        pack_path=output / "pack.json",
        root=ROOT,
        publication=False,
        require_sources=False,
    )
    assert verified["question_count"] == 12
    assert verified["pack_identity_sha256"] == first_pack["pack_identity_sha256"]

    unchanged = instances.read_text()
    instances.write_text(unchanged + "\n")
    with pytest.raises(RepresentativeGoldError, match="question-instance file changed"):
        verify_representative_pack(pack_path=output / "pack.json", root=ROOT, publication=False, require_sources=False)
    instances.write_text(unchanged)

    changed = Path(sql_paths["q84-1"])
    changed.write_text(changed.read_text() + "-- changed\n", encoding="utf-8")
    with pytest.raises(RepresentativeGoldError, match="Reference SQL changed"):
        verify_representative_pack(
            pack_path=output / "pack.json",
            root=ROOT,
            publication=False,
            require_sources=False,
        )
