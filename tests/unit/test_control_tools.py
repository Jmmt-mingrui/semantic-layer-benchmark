from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from runner.core.control_tools import ControlToolDispatcher, ToolProtocolError, validate_read_only_sql
from runner.core.database import DatabaseSettings, connect


ROOT = Path(__file__).parents[2]
CATALOG = json.loads((ROOT / "runner/tools/blank-context.tools.json").read_text())
ALLOWED = {tool["name"] for tool in CATALOG["tools"]}


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO sample VALUES (3)",
        "PRAGMA version",
        "COPY (SELECT 1) TO '/tmp/result.csv'",
        "SELECT * FROM read_csv_auto('/tmp/input.csv')",
        "SELECT 1; SELECT 2",
    ],
)
def test_sql_policy_rejects_non_query_and_external_io(sql: str) -> None:
    with pytest.raises(ToolProtocolError):
        validate_read_only_sql(sql)


def test_sql_policy_accepts_select_and_cte() -> None:
    validate_read_only_sql("SELECT 1")
    validate_read_only_sql("WITH value AS (SELECT 1 AS id) SELECT id FROM value")


def test_control_tools_discover_execute_and_submit(tmp_path: Path) -> None:
    database_path = tmp_path / "control.duckdb"
    with duckdb.connect(str(database_path)) as database:
        database.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, label VARCHAR)")
        database.execute("INSERT INTO sample VALUES (1, 'one'), (2, 'two')")

    settings = DatabaseSettings("duckdb", f"duckdb://{database_path}", None, "main", True)
    with connect(settings) as database:
        dispatcher = ControlToolDispatcher(database, CATALOG, ALLOWED)
        listed = dispatcher.dispatch("db.list_relations", {"schema": "main"}).output
        assert listed == {"relations": [{"schema": "main", "name": "sample", "type": "table"}]}

        described = dispatcher.dispatch("db.describe_relations", {"relations": ["sample"]}).output
        assert [column["name"] for column in described["relations"][0]["columns"]] == ["id", "label"]
        assert described["relations"][0]["columns"][0]["key_role"] == "primary"

        executed = dispatcher.dispatch(
            "db.execute_readonly", {"sql": "SELECT id FROM sample ORDER BY id"}
        ).output
        assert executed["result_handle"] == "result-001"
        assert executed["preview_rows"] == [[1], [2]]
        assert len(executed["result_sha256"]) == 64

        assert dispatcher.dispatch(
            "benchmark.submit_result", {"status": "success", "result_handles": ["result-001"]}
        ).output == {"accepted": True}
        with pytest.raises(ToolProtocolError, match="already"):
            dispatcher.dispatch("benchmark.submit_result", {"status": "failed", "reason": "again"})


def test_dispatcher_enforces_operation_allowlist(tmp_path: Path) -> None:
    database_path = tmp_path / "control.duckdb"
    with duckdb.connect(str(database_path)) as database:
        database.execute("CREATE TABLE sample(id INTEGER)")
    settings = DatabaseSettings("duckdb", f"duckdb://{database_path}", None, "main", True)
    with connect(settings) as database:
        dispatcher = ControlToolDispatcher(database, CATALOG, {"benchmark.submit_result"})
        with pytest.raises(ToolProtocolError, match="not allowed"):
            dispatcher.dispatch("db.list_relations", {})
