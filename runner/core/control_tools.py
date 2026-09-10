from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
import json
import re
from time import perf_counter
from typing import Any

import duckdb
from jsonschema import Draft202012Validator

from runner.core.database import DuckDBAdapter, QueryResult


class ToolProtocolError(ValueError):
    pass


class ToolTimeoutError(TimeoutError):
    pass


_LEADING_QUERY = re.compile(r"^\s*(?:--[^\n]*\n\s*|/\*.*?\*/\s*)*(select|with|values)\b", re.I | re.S)
_FORBIDDEN_SQL = re.compile(
    r"\b(?:pragma|attach|detach|copy|install|load|export|import|call|vacuum|checkpoint|"
    r"read_csv(?:_auto)?|read_json(?:_auto)?|read_parquet|parquet_scan|csv_scan|json_scan|"
    r"sqlite_scan|postgres_scan|mysql_scan|httpfs|glob|query_table|getenv|read_text|read_blob|"
    r"sniff_csv|which_secret|duckdb_secrets)\b",
    re.I,
)
_RELATION = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_read_only_sql(sql: str, max_statements: int = 1) -> None:
    if not isinstance(sql, str) or not sql.strip():
        raise ToolProtocolError("SQL must be a non-empty string")
    try:
        statements = duckdb.extract_statements(sql)
    except duckdb.Error as exc:
        raise ToolProtocolError(f"SQL parse failed: {exc}") from exc
    if not statements or len(statements) > max_statements:
        raise ToolProtocolError(f"Expected 1 to {max_statements} SQL statements")
    if not _LEADING_QUERY.match(sql):
        raise ToolProtocolError("Only SELECT, WITH, or VALUES queries are allowed")
    if _FORBIDDEN_SQL.search(sql):
        raise ToolProtocolError("SQL contains a prohibited operation or external reader")
    if any(str(statement.type) != "StatementType.SELECT" for statement in statements):
        raise ToolProtocolError("Only read-only query statements are allowed")


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def result_payload(result: QueryResult) -> dict[str, Any]:
    return {
        "columns": list(result.columns),
        "rows": [_json_value(row) for row in result.rows],
    }


def result_sha256(result: QueryResult) -> str:
    encoded = json.dumps(
        result_payload(result), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ToolOutcome:
    output: dict[str, Any]
    duration_ms: float


class ControlToolDispatcher:
    def __init__(
        self,
        database: DuckDBAdapter,
        tool_catalog: dict[str, Any],
        allowed_operations: set[str],
        max_database_attempts: int = 3,
        database_timeout_seconds: float = 120,
        preview_rows: int = 20,
    ):
        self.database = database
        self.allowed_operations = allowed_operations
        self.max_database_attempts = max_database_attempts
        self.database_timeout_seconds = database_timeout_seconds
        self.preview_rows = preview_rows
        self._definitions = {tool["name"]: tool for tool in tool_catalog["tools"]}
        self.results: dict[str, QueryResult] = {}
        self.sql_by_handle: dict[str, str] = {}
        self.database_attempts = 0
        self.submission: dict[str, Any] | None = None

    def public_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": name,
                "description": definition["description"],
                "input_schema": definition["input_schema"],
            }
            for name, definition in self._definitions.items()
            if name in self.allowed_operations
        ]

    def dispatch(self, name: str, arguments: dict[str, Any]) -> ToolOutcome:
        started = perf_counter()
        if name not in self.allowed_operations or name not in self._definitions:
            raise ToolProtocolError(f"Operation is not allowed in this condition: {name}")
        errors = sorted(Draft202012Validator(self._definitions[name]["input_schema"]).iter_errors(arguments), key=str)
        if errors:
            raise ToolProtocolError(f"Invalid {name} arguments: {errors[0].message}")
        if name == "db.list_relations":
            output = self._list_relations(arguments)
        elif name == "db.describe_relations":
            output = self._describe_relations(arguments)
        elif name == "db.execute_readonly":
            output = self._execute_readonly(arguments)
        elif name == "benchmark.submit_result":
            output = self._submit(arguments)
        else:
            raise ToolProtocolError(f"No dispatcher is registered for operation: {name}")
        Draft202012Validator(self._definitions[name]["output_schema"]).validate(output)
        return ToolOutcome(output=output, duration_ms=(perf_counter() - started) * 1000)

    def _list_relations(self, arguments: dict[str, Any]) -> dict[str, Any]:
        schema = arguments.get("schema") or self.database.settings.schema
        result = self.database.execute(
            """
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = ?
            ORDER BY table_name
            """,
            (schema,),
        )
        return {
            "relations": [
                {
                    "schema": row[0],
                    "name": row[1],
                    "type": "view" if row[2] == "VIEW" else "table",
                }
                for row in result.rows
            ]
        }

    def _describe_relations(self, arguments: dict[str, Any]) -> dict[str, Any]:
        schema = self.database.settings.schema
        relations = []
        for name in arguments["relations"]:
            if not _RELATION.fullmatch(name):
                raise ToolProtocolError(f"Invalid relation name: {name!r}")
            columns = self.database.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = ? AND table_name = ?
                ORDER BY ordinal_position
                """,
                (schema, name),
            )
            if not columns.rows:
                raise ToolProtocolError(f"Unknown relation: {name}")
            keys = self.database.execute(
                """
                SELECT kcu.column_name, tc.constraint_type
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_catalog = kcu.constraint_catalog
                 AND tc.constraint_schema = kcu.constraint_schema
                 AND tc.constraint_name = kcu.constraint_name
                WHERE tc.table_schema = ? AND tc.table_name = ?
                """,
                (schema, name),
            )
            key_roles = {
                row[0]: {"PRIMARY KEY": "primary", "UNIQUE": "unique", "FOREIGN KEY": "foreign"}.get(row[1], "none")
                for row in keys.rows
            }
            relations.append(
                {
                    "schema": schema,
                    "name": name,
                    "columns": [
                        {
                            "name": row[0],
                            "data_type": row[1],
                            "nullable": row[2] == "YES",
                            "key_role": key_roles.get(row[0], "none"),
                        }
                        for row in columns.rows
                    ],
                }
            )
        return {"relations": relations}

    def _execute_readonly(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.database_attempts >= self.max_database_attempts:
            raise ToolProtocolError("Database attempt budget exhausted")
        self.database_attempts += 1
        sql = arguments["sql"]
        validate_read_only_sql(sql)
        result = self.database.execute(sql, tuple(arguments.get("parameters", ())))
        if result.elapsed_ms > self.database_timeout_seconds * 1000:
            raise ToolTimeoutError("Database query exceeded its configured timeout")
        handle = f"result-{len(self.results) + 1:03d}"
        self.results[handle] = result
        self.sql_by_handle[handle] = sql
        return {
            "result_handle": handle,
            "columns": list(result.columns),
            "row_count": len(result.rows),
            "result_sha256": result_sha256(result),
            "elapsed_ms": result.elapsed_ms,
            "preview_rows": result_payload(result)["rows"][: self.preview_rows],
        }

    def _submit(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.submission is not None:
            raise ToolProtocolError("Result has already been submitted")
        handles = arguments.get("result_handles", [])
        if any(handle not in self.results for handle in handles):
            raise ToolProtocolError("Submission references an unknown result handle")
        self.submission = dict(arguments)
        return {"accepted": True}
