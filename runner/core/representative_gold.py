"""Freeze evaluator-only identities for the representative TPC-DS-derived SF1 suite.

This module never persists reference result rows. It executes each pinned DuckDB
reference statement against one validated local SF1 snapshot and freezes only
column names, row counts, normalized result hashes, and immutable input hashes.

The output is evaluator-only. Target/agent code must never import this module or
receive paths beneath ``benchmark/tpcds/results/gold``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from runner.core.control_tools import result_sha256
from runner.core.database import DatabaseSettings, QueryResult, connect
from runner.core.dataset import validate_sf1_snapshot


REPRESENTATIVE_QUESTION_IDS = (
    "q01", "q02", "q03", "q05", "q12", "q14",
    "q21", "q36", "q39", "q49", "q75", "q84",
)
GOLD_SCHEMA_VERSION = "0.2.0"
SUITE = "representative-v1"
NORMALIZATION_REVISION = "canonical-json-v1"


class RepresentativeGoldError(RuntimeError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(encoded)


def _repo_relative(path: Path, root: Path, *, publication: bool) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError as error:
        if publication:
            raise RepresentativeGoldError(f"Publication input must remain inside repository root: {path}") from error
        return str(resolved)


def load_representative_instances(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise RepresentativeGoldError(f"{source}:{line_number}: invalid JSON") from error
        if not isinstance(value, dict):
            raise RepresentativeGoldError(f"{source}:{line_number}: expected an object")
        rows.append(value)
    ids = tuple(row.get("question_id") for row in rows)
    if ids != REPRESENTATIVE_QUESTION_IDS:
        raise RepresentativeGoldError(
            f"Representative instances must contain exactly {REPRESENTATIVE_QUESTION_IDS}; found {ids}"
        )
    instance_ids = [row.get("instance_id") for row in rows]
    if len(set(instance_ids)) != len(instance_ids) or any(not isinstance(value, str) or not value for value in instance_ids):
        raise RepresentativeGoldError("Representative instance IDs must be unique non-empty strings")
    for row in rows:
        if row.get("benchmark") != "TPC-DS-derived" or row.get("scale_factor") != 1 or row.get("suite") != SUITE:
            raise RepresentativeGoldError(f"{row.get('question_id')}: invalid suite identity")
        target_input = row.get("target_input")
        if not isinstance(target_input, dict) or set(target_input) != {"question"}:
            raise RepresentativeGoldError(f"{row.get('question_id')}: target_input must contain only question")
        references = row.get("evaluator_only", {}).get("reference_sql")
        if not isinstance(references, list) or not references or any(not isinstance(item, str) or not item for item in references):
            raise RepresentativeGoldError(f"{row.get('question_id')}: evaluator_only.reference_sql is required")
        expected_statement_count = 2 if row["question_id"] in {"q14", "q39"} else 1
        if len(references) != expected_statement_count:
            raise RepresentativeGoldError(
                f"{row['question_id']}: expected {expected_statement_count} reference statement(s), found {len(references)}"
            )
    return rows


def _result_identity(result: QueryResult) -> dict[str, Any]:
    return {
        "columns": list(result.columns),
        "row_count": len(result.rows),
        "sha256": result_sha256(QueryResult(columns=result.columns, rows=result.rows, elapsed_ms=0.0)),
        "comparison": "exact_normalized",
        "order_sensitive": True,
        "normalization_revision": NORMALIZATION_REVISION,
    }


def freeze_representative_pack(
    *,
    manifest_path: str | Path,
    instances_path: str | Path,
    output_dir: str | Path,
    root: str | Path = ".",
    publication: bool = True,
    require_sources: bool = True,
) -> dict[str, Any]:
    """Execute and freeze the twelve representative question identities."""

    root_path = Path(root).resolve()
    manifest = Path(manifest_path)
    if not manifest.is_absolute():
        manifest = root_path / manifest
    instances = Path(instances_path)
    if not instances.is_absolute():
        instances = root_path / instances
    destination = Path(output_dir)
    if not destination.is_absolute():
        destination = root_path / destination

    snapshot = validate_sf1_snapshot(
        manifest,
        root=root_path,
        publication=publication,
        require_sources=require_sources,
    )
    manifest_document = json.loads(manifest.read_text(encoding="utf-8"))
    if manifest_document.get("benchmark") != "TPC-DS-derived" or manifest_document.get("scale_factor") != 1:
        raise RepresentativeGoldError("Dataset manifest must identify TPC-DS-derived SF1")
    generator = manifest_document.get("generator", {})
    if generator.get("version") != "4.0.0" or not generator.get("binary_sha256"):
        raise RepresentativeGoldError("Publication requires TPC-DS 4.0.0 dsdgen identity")
    engine = manifest_document.get("engine", {})
    if engine.get("name") != "duckdb" or not engine.get("version"):
        raise RepresentativeGoldError("Dataset manifest must record DuckDB version")

    rows = load_representative_instances(instances)
    schema = json.loads((root_path / "runner/contracts/representative-gold.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    destination.mkdir(parents=True, exist_ok=True)

    settings = DatabaseSettings("duckdb", f"duckdb://{snapshot['database_path']}", None, "main", True)
    frozen: list[dict[str, Any]] = []
    with connect(settings) as database:
        for instance in rows:
            statement_artifacts: list[dict[str, Any]] = []
            for statement_index, reference in enumerate(instance["evaluator_only"]["reference_sql"], start=1):
                reference_path = Path(reference)
                if not reference_path.is_absolute():
                    reference_path = root_path / reference_path
                if not reference_path.is_file():
                    raise RepresentativeGoldError(f"Missing DuckDB reference SQL for {instance['question_id']}: {reference}")
                sql = reference_path.read_text(encoding="utf-8")
                result = database.execute(sql)
                statement_artifacts.append(
                    {
                        "statement_index": statement_index,
                        "reference_sql": {
                            "path": _repo_relative(reference_path, root_path, publication=publication),
                            "sha256": _sha256_file(reference_path),
                        },
                        "result": _result_identity(result),
                    }
                )

            artifact = {
                "schema_version": GOLD_SCHEMA_VERSION,
                "benchmark": "TPC-DS-derived",
                "scale_factor": 1,
                "suite": SUITE,
                "question_id": instance["question_id"],
                "instance_id": instance["instance_id"],
                "dataset": {
                    "manifest_path": _repo_relative(manifest, root_path, publication=publication),
                    "manifest_sha256": snapshot["manifest_sha256"],
                    "dataset_sha256": snapshot["dataset_sha256"],
                    "database_sha256": snapshot["database_sha256"],
                    "logical_snapshot_identity": manifest_document["dataset_sha256"],
                },
                "question_instance": {
                    "path": _repo_relative(instances, root_path, publication=publication),
                    "line_sha256": _canonical_json_sha256(instance),
                },
                "statements": statement_artifacts,
                "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }
            errors = sorted(validator.iter_errors(artifact), key=str)
            if errors:
                raise RepresentativeGoldError(f"Invalid Gold artifact for {instance['question_id']}: {errors[0].message}")
            path = destination / f"{instance['question_id']}.json"
            path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            frozen.append(artifact)

    pack = {
        "schema_version": GOLD_SCHEMA_VERSION,
        "benchmark": "TPC-DS-derived",
        "scale_factor": 1,
        "suite": SUITE,
        "question_ids": list(REPRESENTATIVE_QUESTION_IDS),
        "question_count": len(REPRESENTATIVE_QUESTION_IDS),
        "statement_count": sum(len(item["statements"]) for item in frozen),
        "manifest_path": _repo_relative(manifest, root_path, publication=publication),
        "manifest_sha256": snapshot["manifest_sha256"],
        "instances_path": _repo_relative(instances, root_path, publication=publication),
        "instances_sha256": _sha256_file(instances),
        "gold": [
            {
                "question_id": item["question_id"],
                "path": _repo_relative(destination / f"{item['question_id']}.json", root_path, publication=publication),
                "sha256": _sha256_file(destination / f"{item['question_id']}.json"),
            }
            for item in frozen
        ],
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    pack["pack_identity_sha256"] = _canonical_json_sha256({key: value for key, value in pack.items() if key != "generated_at"})
    (destination / "pack.json").write_text(json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return pack


def verify_representative_pack(
    *,
    pack_path: str | Path,
    root: str | Path = ".",
    publication: bool = True,
    require_sources: bool = True,
) -> dict[str, Any]:
    """Fail closed if any dataset, instance, reference SQL, or Gold input changed."""

    root_path = Path(root).resolve()
    path = Path(pack_path)
    if not path.is_absolute():
        path = root_path / path
    pack = json.loads(path.read_text(encoding="utf-8"))
    if pack.get("benchmark") != "TPC-DS-derived" or pack.get("suite") != SUITE:
        raise RepresentativeGoldError("Unexpected representative pack identity")
    if tuple(pack.get("question_ids", ())) != REPRESENTATIVE_QUESTION_IDS or pack.get("question_count") != 12:
        raise RepresentativeGoldError("Representative pack must contain exactly the twelve selected questions")

    manifest = Path(pack["manifest_path"])
    if not manifest.is_absolute():
        manifest = root_path / manifest
    snapshot = validate_sf1_snapshot(manifest, root=root_path, publication=publication, require_sources=require_sources)
    if snapshot["manifest_sha256"] != pack["manifest_sha256"]:
        raise RepresentativeGoldError("Dataset manifest changed after Gold freeze")
    instances = Path(pack["instances_path"])
    if not instances.is_absolute():
        instances = root_path / instances
    if _sha256_file(instances) != pack["instances_sha256"]:
        raise RepresentativeGoldError("Representative question-instance file changed after Gold freeze")
    rows = {row["question_id"]: row for row in load_representative_instances(instances)}

    schema = json.loads((root_path / "runner/contracts/representative-gold.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    statement_count = 0
    for entry in pack["gold"]:
        question_id = entry["question_id"]
        gold_path = Path(entry["path"])
        if not gold_path.is_absolute():
            gold_path = root_path / gold_path
        if _sha256_file(gold_path) != entry["sha256"]:
            raise RepresentativeGoldError(f"Frozen Gold file changed for {question_id}")
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(gold), key=str)
        if errors:
            raise RepresentativeGoldError(f"Invalid Gold artifact for {question_id}: {errors[0].message}")
        if gold["dataset"]["manifest_sha256"] != pack["manifest_sha256"]:
            raise RepresentativeGoldError(f"Gold manifest binding changed for {question_id}")
        instance = rows[question_id]
        if gold["instance_id"] != instance["instance_id"] or gold["question_instance"]["line_sha256"] != _canonical_json_sha256(instance):
            raise RepresentativeGoldError(f"Question instance changed for {question_id}")
        references = instance["evaluator_only"]["reference_sql"]
        if len(references) != len(gold["statements"]):
            raise RepresentativeGoldError(f"Reference statement count changed for {question_id}")
        for reference, statement in zip(references, gold["statements"], strict=True):
            reference_path = Path(reference)
            if not reference_path.is_absolute():
                reference_path = root_path / reference_path
            expected_ref = _repo_relative(reference_path, root_path, publication=publication)
            if statement["reference_sql"]["path"] != expected_ref or statement["reference_sql"]["sha256"] != _sha256_file(reference_path):
                raise RepresentativeGoldError(f"Reference SQL changed for {question_id}")
        statement_count += len(gold["statements"])
    if statement_count != pack["statement_count"]:
        raise RepresentativeGoldError("Representative statement count changed")
    expected_identity = _canonical_json_sha256(
        {key: value for key, value in pack.items() if key not in {"generated_at", "pack_identity_sha256"}}
    )
    if expected_identity != pack["pack_identity_sha256"]:
        raise RepresentativeGoldError("Representative pack identity does not match its frozen inputs")
    return {
        "question_count": 12,
        "statement_count": statement_count,
        "dataset_sha256": snapshot["dataset_sha256"],
        "pack_identity_sha256": pack["pack_identity_sha256"],
    }
