from __future__ import annotations

import argparse
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
    args = parser.parse_args()
    args.database.parent.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    manifest = {"scale_factor": 1, "engine": "duckdb", "tables": {}}
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
    manifest["elapsed_ms"] = round((perf_counter() - started) * 1000, 3)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
