from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from time import perf_counter

import duckdb
from jsonschema import Draft202012Validator, FormatChecker

from runner.core.dataset import TPCDS_TABLES, checksum, snapshot_checksum

TABLES = TPCDS_TABLES


def quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def require_generated_sources(input_directory: Path) -> dict[str, Path]:
    sources = {table: input_directory / f"{table}.dat" for table in TABLES}
    missing = [str(path) for path in sources.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing generated inputs: " + ", ".join(missing))
    return sources


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
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing target database after all generated inputs pass preflight",
    )
    args = parser.parse_args()
    if args.generator_binary is not None and not args.generator_binary.is_file():
        raise FileNotFoundError(f"Generator binary not found: {args.generator_binary}")
    if not args.schema.is_file():
        raise FileNotFoundError(f"Schema file not found: {args.schema}")
    sources = require_generated_sources(args.input)
    if args.database.exists() and not args.overwrite:
        raise FileExistsError(
            f"Database already exists: {args.database}; pass --overwrite to replace it"
        )
    if args.overwrite and args.database.exists():
        args.database.unlink()
    wal_path = Path(str(args.database) + ".wal")
    if args.overwrite and wal_path.exists():
        wal_path.unlink()
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
            source = sources[table]
            manifest["tables"][table] = {
                "source": str(source),
                "sha256": checksum(source),
                "rows": load_table(connection, table, source),
            }
    manifest["database"]["sha256"] = checksum(args.database)
    manifest["dataset_sha256"] = snapshot_checksum(schema_sha256, manifest["tables"])
    manifest["generated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    manifest["elapsed_ms"] = round((perf_counter() - started) * 1000, 3)
    manifest_schema = json.loads(Path("runner/contracts/dataset-manifest.schema.json").read_text())
    Draft202012Validator(manifest_schema, format_checker=FormatChecker()).validate(manifest)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
