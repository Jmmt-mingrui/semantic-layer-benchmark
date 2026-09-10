from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from time import perf_counter

import duckdb


TABLES = (
    "call_center", "catalog_page", "catalog_returns", "catalog_sales", "customer",
    "customer_address", "customer_demographics", "date_dim", "dbgen_version",
    "household_demographics", "income_band", "inventory", "item", "promotion",
    "reason", "ship_mode", "store", "store_returns", "store_sales", "time_dim",
    "warehouse", "web_page", "web_returns", "web_sales", "web_site",
)


def quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_checksum(schema_sha256: str, tables: dict[str, dict[str, object]]) -> str:
    identity = {
        "schema_sha256": schema_sha256,
        "tables": {
            name: {"rows": values["rows"], "sha256": values["sha256"]}
            for name, values in sorted(tables.items())
        },
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_table(connection: duckdb.DuckDBPyConnection, table: str, source: Path) -> int:
    columns = connection.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'main' AND table_name = ? ORDER BY ordinal_position",
        [table],
    ).fetchall()
    if not columns:
        raise ValueError(f"Table not found in schema: {table}")
    csv_columns = {name: data_type for name, data_type in columns}
    csv_columns["_trailing_delimiter"] = "VARCHAR"
    relation = connection.read_csv(
        str(source), delimiter="|", header=False, columns=csv_columns, strict_mode=True
    )
    relation.project(", ".join(quote(name) for name, _ in columns)).insert_into(f"main.{quote(table)}")
    return connection.execute(f"SELECT count(*) FROM main.{quote(table)}").fetchone()[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a DuckDB TPC-DS SF1 database from dsdgen .dat files")
    parser.add_argument("--input", type=Path, default=Path("data/tpcds/sf1/generated"))
    parser.add_argument("--database", type=Path, default=Path("data/tpcds/sf1/tpcds.duckdb"))
    parser.add_argument("--schema", type=Path, default=Path("data/tpcds/schema/duckdb/schema.sql"))
    parser.add_argument("--manifest", type=Path, default=Path("data/tpcds/sf1/manifests/duckdb-sf1.json"))
    parser.add_argument("--generator-version", default="4.0.0")
    parser.add_argument("--generator-binary", type=Path)
    args = parser.parse_args()
    if args.generator_binary is not None and not args.generator_binary.is_file():
        raise FileNotFoundError(f"Generator binary not found: {args.generator_binary}")
    args.database.parent.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    schema_sha256 = checksum(args.schema)
    manifest = {
        "schema_version": "0.1.0",
        "benchmark": "TPC-DS-derived",
        "scale_factor": 1,
        "generator": {
            "name": "dsdgen",
            "version": args.generator_version,
            "binary_sha256": checksum(args.generator_binary) if args.generator_binary else None,
        },
        "engine": {"name": "duckdb", "version": duckdb.__version__},
        "schema": {"path": str(args.schema), "sha256": schema_sha256},
        "database": {"path": str(args.database)},
        "tables": {},
    }
    with duckdb.connect(str(args.database)) as connection:
        connection.execute(args.schema.read_text())
        for table in TABLES:
            source = args.input / f"{table}.dat"
            if not source.exists():
                raise FileNotFoundError(f"Missing generated input: {source}")
            manifest["tables"][table] = {
                "source": str(source),
                "sha256": checksum(source),
                "rows": load_table(connection, table, source),
            }
    manifest["database"]["sha256"] = checksum(args.database)
    manifest["dataset_sha256"] = snapshot_checksum(schema_sha256, manifest["tables"])
    manifest["generated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    manifest["elapsed_ms"] = round((perf_counter() - started) * 1000, 3)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
