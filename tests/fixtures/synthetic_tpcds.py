from __future__ import annotations

from datetime import date, time
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any

import duckdb

from runner.core.dataset import TPCDS_TABLES


FIXTURE_KIND = "synthetic_protocol_fixture"
FIXTURE_REVISION = "synthetic-tpcds-protocol-v1"
_PROHIBITED_OUTPUT_ROOTS = (
    Path("data/tpcds/sf1"),
    Path("benchmark/tpcds/results/gold"),
    Path("runs"),
    Path("reports/generated"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _assert_test_only_path(path: Path, repository_root: Path) -> None:
    resolved = path.resolve()
    for relative_root in _PROHIBITED_OUTPUT_ROOTS:
        prohibited = (repository_root / relative_root).resolve()
        if resolved == prohibited or resolved.is_relative_to(prohibited):
            raise ValueError(
                f"Synthetic fixtures cannot be written under benchmark output root: {relative_root}"
            )


def _value_for_type(sql_type: str) -> Any:
    normalized = sql_type.upper()
    if "INT" in normalized:
        return 1
    if normalized.startswith(("DECIMAL", "NUMERIC")):
        return Decimal("1.00")
    if normalized == "DATE":
        return date(2000, 1, 1)
    if normalized.startswith("TIME"):
        return time(0, 0, 0)
    if normalized.startswith(("CHAR", "VARCHAR", "TEXT")):
        return "X"
    if normalized == "BOOLEAN":
        return False
    raise ValueError(f"Unsupported fixture column type: {sql_type}")


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, time)):
        return value.isoformat()
    return value


def _logical_identity(connection: duckdb.DuckDBPyConnection, schema_sha256: str) -> str:
    tables: dict[str, Any] = {}
    for table in sorted(TPCDS_TABLES):
        columns = connection.execute(f"PRAGMA table_info('{table}')").fetchall()
        rows = connection.execute(f'SELECT * FROM "{table}"').fetchall()
        tables[table] = {
            "columns": [
                {
                    "name": column[1],
                    "type": column[2],
                    "not_null": bool(column[3]),
                    "primary_key": bool(column[5]),
                }
                for column in columns
            ],
            "rows": [[_canonical_value(value) for value in row] for row in rows],
        }
    payload = {
        "fixture_revision": FIXTURE_REVISION,
        "schema_sha256": schema_sha256,
        "tables": tables,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def create_synthetic_tpcds_fixture(
    database_path: str | Path,
    *,
    repository_root: str | Path = ".",
    schema_path: str | Path = "data/tpcds/schema/duckdb/schema.sql",
) -> dict[str, Any]:
    """Create a deterministic test-only database with one synthetic row per TPC-DS table.

    The returned identity is intentionally incompatible with the publishable SF1
    dataset manifest. The function also refuses every production benchmark output
    tree so callers cannot accidentally promote this fixture to a scored artifact.
    """

    root = Path(repository_root).resolve()
    destination = Path(database_path)
    if not destination.is_absolute():
        destination = root / destination
    destination = destination.resolve()
    schema = Path(schema_path)
    if not schema.is_absolute():
        schema = root / schema
    schema = schema.resolve()
    metadata_path = destination.with_suffix(destination.suffix + ".fixture.json")

    _assert_test_only_path(destination, root)
    _assert_test_only_path(metadata_path, root)
    if destination.exists() or metadata_path.exists():
        raise FileExistsError("Synthetic fixture outputs must not already exist")
    if not schema.is_file():
        raise FileNotFoundError(f"DuckDB schema not found: {schema}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(destination))
    try:
        connection.execute(schema.read_text())
        actual_tables = tuple(
            row[0]
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main' AND table_type = 'BASE TABLE' "
                "ORDER BY table_name"
            ).fetchall()
        )
        expected_tables = tuple(sorted(TPCDS_TABLES))
        if actual_tables != expected_tables:
            raise ValueError(
                f"Fixture schema must contain exactly the 25 physical tables: {actual_tables}"
            )

        for table in TPCDS_TABLES:
            columns = connection.execute(f"PRAGMA table_info('{table}')").fetchall()
            values = [_value_for_type(column[2]) for column in columns]
            if table == "dbgen_version":
                values = [
                    "SYNTHETIC",
                    date(1970, 1, 1),
                    time(0, 0, 0),
                    "NON-PUBLISHABLE PROTOCOL FIXTURE; NOT TPC-DS SF1",
                ]
            placeholders = ", ".join("?" for _ in columns)
            connection.execute(f'INSERT INTO "{table}" VALUES ({placeholders})', values)

        schema_sha256 = _sha256(schema)
        logical_sha256 = _logical_identity(connection, schema_sha256)
        connection.execute("CHECKPOINT")
    except Exception:
        connection.close()
        if destination.exists():
            destination.unlink()
        raise
    else:
        connection.close()

    identity = {
        "artifact_type": FIXTURE_KIND,
        "fixture_revision": FIXTURE_REVISION,
        "purpose": ["protocol tests", "continuous integration"],
        "publishable": False,
        "ranking_eligible": False,
        "tpcds_equivalence": "none",
        "scale_factor": None,
        "gold_results": "forbidden",
        "table_count": len(TPCDS_TABLES),
        "row_policy": "exactly-one-synthetic-row-per-table",
        "schema_sha256": schema_sha256,
        "logical_sha256": logical_sha256,
    }
    metadata_path.write_text(
        json.dumps(identity, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return identity
