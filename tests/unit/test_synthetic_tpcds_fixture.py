from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from runner.core.dataset import TPCDS_TABLES
from tests.fixtures.synthetic_tpcds import (
    FIXTURE_KIND,
    create_synthetic_tpcds_fixture,
)


ROOT = Path(__file__).parents[2]


def test_fixture_has_all_tables_and_is_explicitly_unranked(tmp_path: Path) -> None:
    database = tmp_path / "protocol.duckdb"
    identity = create_synthetic_tpcds_fixture(database, repository_root=ROOT)

    assert identity["artifact_type"] == FIXTURE_KIND
    assert identity["publishable"] is False
    assert identity["ranking_eligible"] is False
    assert identity["tpcds_equivalence"] == "none"
    assert identity["scale_factor"] is None
    assert identity["gold_results"] == "forbidden"
    assert "benchmark" not in identity

    persisted = json.loads(database.with_suffix(".duckdb.fixture.json").read_text())
    assert persisted == identity

    connection = duckdb.connect(str(database), read_only=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main' AND table_type = 'BASE TABLE'"
            ).fetchall()
        }
        assert tables == set(TPCDS_TABLES)
        assert all(
            connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0] == 1
            for table in TPCDS_TABLES
        )
        assert connection.execute("SELECT dv_version FROM dbgen_version").fetchone()[0] == "SYNTHETIC"
    finally:
        connection.close()


def test_fixture_logical_identity_is_deterministic(tmp_path: Path) -> None:
    first = create_synthetic_tpcds_fixture(tmp_path / "first.duckdb", repository_root=ROOT)
    second = create_synthetic_tpcds_fixture(tmp_path / "second.duckdb", repository_root=ROOT)

    assert first["logical_sha256"] == second["logical_sha256"]

    connection = duckdb.connect(str(tmp_path / "first.duckdb"), read_only=True)
    try:
        joined = connection.execute(
            "SELECT count(*) FROM store_sales ss "
            "JOIN item i ON i.i_item_sk = ss.ss_item_sk "
            "JOIN date_dim d ON d.d_date_sk = ss.ss_sold_date_sk"
        ).fetchone()[0]
        assert joined == 1
    finally:
        connection.close()


@pytest.mark.parametrize(
    "relative_path",
    [
        "data/tpcds/sf1/synthetic.duckdb",
        "benchmark/tpcds/results/gold/synthetic.duckdb",
        "runs/synthetic.duckdb",
        "reports/generated/synthetic.duckdb",
    ],
)
def test_fixture_refuses_benchmark_output_trees(relative_path: str) -> None:
    destination = ROOT / relative_path

    with pytest.raises(ValueError, match="cannot be written"):
        create_synthetic_tpcds_fixture(destination, repository_root=ROOT)

    assert not destination.exists()


def test_fixture_refuses_to_replace_existing_output(tmp_path: Path) -> None:
    destination = tmp_path / "existing.duckdb"
    destination.write_bytes(b"owned by another test")

    with pytest.raises(FileExistsError, match="must not already exist"):
        create_synthetic_tpcds_fixture(destination, repository_root=ROOT)

    assert destination.read_bytes() == b"owned by another test"
