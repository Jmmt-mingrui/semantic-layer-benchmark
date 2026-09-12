from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

import duckdb
from jsonschema import Draft202012Validator, FormatChecker

from runner.core.control_tools import result_sha256
from runner.core.database import DatabaseSettings, QueryResult, connect


TPCDS_TABLES = (
    "call_center",
    "catalog_page",
    "catalog_returns",
    "catalog_sales",
    "customer",
    "customer_address",
    "customer_demographics",
    "date_dim",
    "dbgen_version",
    "household_demographics",
    "income_band",
    "inventory",
    "item",
    "promotion",
    "reason",
    "ship_mode",
    "store",
    "store_returns",
    "store_sales",
    "time_dim",
    "warehouse",
    "web_page",
    "web_returns",
    "web_sales",
    "web_site",
)


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_checksum(schema_sha256: str, tables: dict[str, dict[str, Any]]) -> str:
    identity = {
        "schema_sha256": schema_sha256,
        "tables": {
            table: {"rows": item["rows"], "sha256": item["sha256"]}
            for table, item in sorted(tables.items())
        },
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _resolve_manifest_path(root: Path, value: str, publication: bool) -> Path:
    declared = Path(value)
    if publication and declared.is_absolute():
        raise ValueError(f"Publication manifests require repository-relative paths: {value}")
    resolved = declared if declared.is_absolute() else root / declared
    resolved = resolved.resolve()
    if publication and not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Manifest path escapes repository root: {value}")
    return resolved


def _require_repository_path(path: Path, root: Path, label: str) -> None:
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Publication {label} must be inside the repository root: {path}")


def validate_sf1_snapshot(
    manifest_path: str | Path,
    *,
    root: str | Path = ".",
    publication: bool = False,
    require_sources: bool = False,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    manifest_file = Path(manifest_path)
    if not manifest_file.is_absolute():
        manifest_file = root_path / manifest_file
    manifest = json.loads(manifest_file.read_text())
    schema = json.loads((root_path / "runner/contracts/dataset-manifest.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest)

    if manifest["generator"]["version"] != "4.0.0":
        raise ValueError("The frozen baseline requires TPC-DS dsdgen v4.0.0")
    if publication and manifest["generator"]["binary_sha256"] is None:
        raise ValueError("Publication requires the dsdgen binary SHA-256")
    if manifest["engine"]["version"] != duckdb.__version__:
        raise ValueError(
            f"Manifest DuckDB version {manifest['engine']['version']} does not match runtime {duckdb.__version__}"
        )

    schema_path = _resolve_manifest_path(root_path, manifest["schema"]["path"], publication)
    database_path = _resolve_manifest_path(root_path, manifest["database"]["path"], publication)
    if checksum(schema_path) != manifest["schema"]["sha256"]:
        raise ValueError("Physical schema SHA-256 does not match the manifest")
    if checksum(database_path) != manifest["database"]["sha256"]:
        raise ValueError("DuckDB database SHA-256 does not match the manifest")
    calculated_snapshot = snapshot_checksum(manifest["schema"]["sha256"], manifest["tables"])
    if calculated_snapshot != manifest["dataset_sha256"]:
        raise ValueError("Logical dataset SHA-256 does not match the manifest")

    if require_sources:
        for name in TPCDS_TABLES:
            source = _resolve_manifest_path(root_path, manifest["tables"][name]["source"], publication)
            if checksum(source) != manifest["tables"][name]["sha256"]:
                raise ValueError(f"Generated source SHA-256 does not match for table: {name}")

    settings = DatabaseSettings("duckdb", f"duckdb://{database_path}", None, "main", True)
    actual_rows: dict[str, int] = {}
    with connect(settings) as database:
        for name in TPCDS_TABLES:
            row_count = int(database.execute(f'SELECT count(*) FROM "{name}"').rows[0][0])
            expected = int(manifest["tables"][name]["rows"])
            if row_count != expected:
                raise ValueError(f"Row count mismatch for {name}: expected {expected}, found {row_count}")
            actual_rows[name] = row_count

    return {
        "manifest": manifest,
        "manifest_path": manifest_file.resolve(),
        "manifest_sha256": checksum(manifest_file),
        "schema_path": schema_path,
        "database_path": database_path,
        "database_sha256": manifest["database"]["sha256"],
        "dataset_sha256": manifest["dataset_sha256"],
        "table_count": len(actual_rows),
        "total_rows": sum(actual_rows.values()),
    }


def freeze_gold_result(
    manifest_path: str | Path,
    question_instances_path: str | Path,
    output_path: str | Path,
    *,
    question_id: str = "q01",
    root: str | Path = ".",
    publication: bool = False,
    require_sources: bool = False,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    snapshot = validate_sf1_snapshot(
        manifest_path,
        root=root_path,
        publication=publication,
        require_sources=require_sources,
    )
    question_file = Path(question_instances_path)
    if not question_file.is_absolute():
        question_file = root_path / question_file
    if publication:
        _require_repository_path(question_file, root_path, "question instance")
    questions = [json.loads(line) for line in question_file.read_text().splitlines() if line.strip()]
    matches = [item for item in questions if item["question_id"] == question_id]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one materialized instance for {question_id}")
    question = matches[0]
    Draft202012Validator(
        json.loads((root_path / "runner/contracts/question-instance.schema.json").read_text())
    ).validate(question)
    contract = question["evaluator_only"]["result_contract"]
    if (
        question["evaluator_only"]["expected_statement_count"] != 1
        or contract["comparison"] != "exact_normalized"
        or not contract["order_sensitive"]
    ):
        raise ValueError("Gold freeze v0.1 supports one order-sensitive exact-normalized result")

    reference_value = question["evaluator_only"]["reference_sql"][0]
    reference_path = Path(reference_value)
    if not reference_path.is_absolute():
        reference_path = root_path / reference_path
    if publication:
        _require_repository_path(reference_path, root_path, "reference SQL")
    reference_sql = reference_path.read_text()
    settings = DatabaseSettings("duckdb", f"duckdb://{snapshot['database_path']}", None, "main", True)
    with connect(settings) as database:
        result = database.execute(reference_sql)
    if list(result.columns) != contract["columns"]:
        raise ValueError(
            f"Reference result columns do not match the question contract: {list(result.columns)}"
        )
    if contract.get("max_rows") is not None and len(result.rows) > contract["max_rows"]:
        raise ValueError("Reference result exceeds the declared maximum row count")

    def path_ref(path: Path) -> str:
        try:
            return str(path.resolve().relative_to(root_path))
        except ValueError:
            return str(path.resolve())

    artifact = {
        "schema_version": "0.1.0",
        "benchmark": "TPC-DS-derived",
        "scale_factor": 1,
        "question_id": question["question_id"],
        "instance_id": question["instance_id"],
        "dataset": {
            "manifest_path": path_ref(snapshot["manifest_path"]),
            "manifest_sha256": snapshot["manifest_sha256"],
            "dataset_sha256": snapshot["dataset_sha256"],
            "database_sha256": snapshot["database_sha256"],
        },
        "question_instance": {"path": path_ref(question_file), "sha256": checksum(question_file)},
        "reference_sql": {"path": path_ref(reference_path), "sha256": checksum(reference_path)},
        "result": {
            "columns": list(result.columns),
            "row_count": len(result.rows),
            "sha256": result_sha256(
                QueryResult(columns=result.columns, rows=result.rows, elapsed_ms=0.0)
            ),
            "comparison": "exact_normalized",
            "order_sensitive": True,
            "normalization_revision": "canonical-json-v1",
        },
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    gold_schema = json.loads((root_path / "runner/contracts/gold-result.schema.json").read_text())
    Draft202012Validator(gold_schema, format_checker=FormatChecker()).validate(artifact)
    destination = Path(output_path)
    if not destination.is_absolute():
        destination = root_path / destination
    if publication:
        _require_repository_path(destination, root_path, "gold output")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return artifact
