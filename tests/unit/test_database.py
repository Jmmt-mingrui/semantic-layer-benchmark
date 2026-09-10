from pathlib import Path

import duckdb
import pytest

from runner.core.database import DatabaseSettings, connect, duckdb_path_from_url
from scripts.load_tpcds_sf1 import TABLES, load_table, require_generated_sources


def test_relative_duckdb_url() -> None:
    assert duckdb_path_from_url("duckdb:///./data/test.duckdb") == "data/test.duckdb"


def test_rejects_non_duckdb_url() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        duckdb_path_from_url("postgresql://localhost/example")


def test_read_only_adapter_executes_query(tmp_path: Path) -> None:
    database = tmp_path / "test.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute("CREATE TABLE sample(id INTEGER)")
        connection.execute("INSERT INTO sample VALUES (1), (2)")
    settings = DatabaseSettings("duckdb", f"duckdb://{database}", None, "main", True)
    with connect(settings) as adapter:
        result = adapter.execute("SELECT sum(id) AS total FROM sample")
    assert result.columns == ("total",)
    assert result.rows == [(3,)]
    assert result.elapsed_ms >= 0


def test_load_table_accepts_tpcds_trailing_delimiter(tmp_path: Path) -> None:
    source = tmp_path / "sample.dat"
    source.write_text("1|alpha|\n2||\n")
    with duckdb.connect(":memory:") as connection:
        connection.execute("CREATE TABLE main.sample(id INTEGER, label VARCHAR)")
        assert load_table(connection, "sample", source) == 2
        assert connection.execute("SELECT * FROM sample ORDER BY id").fetchall() == [(1, "alpha"), (2, None)]


def test_generated_source_preflight_reports_all_missing_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError) as error:
        require_generated_sources(tmp_path)
    assert str(tmp_path / f"{TABLES[0]}.dat") in str(error.value)
    assert str(tmp_path / f"{TABLES[-1]}.dat") in str(error.value)
