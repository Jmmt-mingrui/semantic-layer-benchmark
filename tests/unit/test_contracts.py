from __future__ import annotations

import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator
import yaml

from scripts.load_tpcds_sf1 import TABLES, snapshot_checksum


ROOT = Path(__file__).parents[2]
CONTRACTS = ROOT / "runner" / "contracts"
CONFIG = ROOT / "runner" / "config" / "native-sf1-q01.yaml"
CONTROL_CONFIG = ROOT / "runner" / "config" / "control-sf1-q01.yaml"
TARGETS = ROOT / "runner" / "config" / "targets.native.yaml"
QUESTIONS = ROOT / "benchmark" / "tpcds" / "questions" / "instances" / "sf1-qualification-q01.jsonl"
TRANSCRIPT = ROOT / "runner" / "examples" / "blank-context-q01.transcript.yaml"
BLANK_TOOLS = ROOT / "runner" / "tools" / "blank-context.tools.json"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def test_contracts_are_unique_draft_2020_12_schemas() -> None:
    schemas = [json.loads(path.read_text()) for path in sorted(CONTRACTS.glob("*.schema.json"))]
    assert {schema["title"] for schema in schemas} == {
        "Semantic layer benchmark experiment",
        "Materialized benchmark question instance",
        "TPC-DS-derived dataset manifest",
        "Benchmark run record",
        "Benchmark trial record",
        "Sanitized benchmark trace event",
    }
    assert all(schema["$schema"] == "https://json-schema.org/draft/2020-12/schema" for schema in schemas)
    ids = [schema["$id"] for schema in schemas]
    assert len(ids) == len(set(ids))
    for schema in schemas:
        Draft202012Validator.check_schema(schema)


def test_dataset_identity_is_stable_and_content_sensitive() -> None:
    schema_sha256 = "a" * 64
    first = {
        "store": {"rows": 2, "sha256": "b" * 64},
        "customer": {"rows": 1, "sha256": "c" * 64},
    }
    reordered = {"customer": first["customer"], "store": first["store"]}
    changed = {**first, "store": {"rows": 3, "sha256": "b" * 64}}
    assert snapshot_checksum(schema_sha256, first) == snapshot_checksum(schema_sha256, reordered)
    assert snapshot_checksum(schema_sha256, first) != snapshot_checksum(schema_sha256, changed)


def test_dataset_manifest_shape_accepts_loader_output() -> None:
    schema_sha256 = "a" * 64
    tables = {
        name: {"source": f"generated/{name}.dat", "rows": index, "sha256": f"{index + 1:064x}"}
        for index, name in enumerate(TABLES)
    }
    manifest = {
        "schema_version": "0.1.0",
        "benchmark": "TPC-DS-derived",
        "scale_factor": 1,
        "generator": {
            "name": "dsdgen",
            "version": "4.0.0",
            "binary_sha256": None,
        },
        "engine": {"name": "duckdb", "version": "1.4.0"},
        "schema": {"path": "schema.sql", "sha256": schema_sha256},
        "database": {"path": "tpcds.duckdb", "sha256": "b" * 64},
        "tables": tables,
        "dataset_sha256": snapshot_checksum(schema_sha256, tables),
        "generated_at": "2026-09-10T00:00:00Z",
        "elapsed_ms": 1.0,
    }
    schema = json.loads((CONTRACTS / "dataset-manifest.schema.json").read_text())
    Draft202012Validator(schema).validate(manifest)


def test_pilot_config_conforms_to_experiment_schema() -> None:
    schema = json.loads((CONTRACTS / "experiment.schema.json").read_text())
    Draft202012Validator(schema).validate(load_yaml(CONFIG))
    Draft202012Validator(schema).validate(load_yaml(CONTROL_CONFIG))
    assert load_yaml(CONTROL_CONFIG)["targets"]["include"] == ["blank_context", "ddl_only"]


def test_native_registry_preserves_every_target_surface() -> None:
    registry = load_yaml(TARGETS)
    targets = registry["targets"]
    assert set(targets) == {
        "blank_context",
        "ddl_only",
        "metricflow",
        "cube",
        "ossie",
        "okf",
        "skill",
    }
    assert registry["policy"]["primary_lane"] == "native_end_to_end"
    assert registry["policy"]["normalize_to_shared_context"] is False
    assert registry["policy"]["undeclared_fallback"] == "forbidden"

    for engine in ("metricflow", "cube"):
        prohibited = targets[engine]["prohibited_operations"]
        assert "db.execute_readonly" in prohibited
        assert targets[engine]["native_surface"]["result_origin"] == "native_engine"

    assert targets["okf"]["native_surface"]["name"] == "okf_markdown_bundle"
    assert "skill.preload_all_references" in targets["skill"]["prohibited_operations"]
    assert targets["ossie"]["role"] == "semantic_interchange_specification"


def test_blank_context_pilot_has_no_preloaded_semantics() -> None:
    experiment = load_yaml(CONFIG)
    blank = load_yaml(TARGETS)["targets"]["blank_context"]

    assert experiment["lane"] == "native_end_to_end"
    assert experiment["targets"]["include"] == ["blank_context"]
    assert experiment["targets"]["native_only"] is True
    assert experiment["agent"]["fresh_conversation_per_trial"] is True
    assert experiment["isolation"]["gold_assets"] == "evaluator_only"
    assert experiment["isolation"]["cross_trial_memory"] == "disabled"
    assert blank["initial_semantic_context"] == "none"
    assert blank["native_surface"]["artifact_root"] is None
    assert ROOT / blank["native_surface"]["tool_catalog"] == BLANK_TOOLS
    assert blank["allowed_operations"] == [
        "db.list_relations",
        "db.describe_relations",
        "db.execute_readonly",
        "benchmark.submit_result",
    ]


def test_blank_context_tool_catalog_is_closed_and_valid() -> None:
    catalog = json.loads(BLANK_TOOLS.read_text())
    assert catalog["catalog"] == "blank_context"
    names = [tool["name"] for tool in catalog["tools"]]
    assert names == [
        "db.list_relations",
        "db.describe_relations",
        "db.execute_readonly",
        "benchmark.submit_result",
    ]
    for tool in catalog["tools"]:
        for key in ("input_schema", "output_schema"):
            schema = tool[key]
            Draft202012Validator.check_schema(schema)
            assert schema["additionalProperties"] is False


def test_q01_instance_separates_target_input_from_gold() -> None:
    records = [json.loads(line) for line in QUESTIONS.read_text().splitlines() if line.strip()]
    assert len(records) == 1
    record = records[0]
    schema = json.loads((CONTRACTS / "question-instance.schema.json").read_text())
    Draft202012Validator(schema).validate(record)
    target_input = record["target_input"]
    orchestrator_only = record["orchestrator_only"]
    evaluator_only = record["evaluator_only"]

    assert record["question_id"] == "q01"
    assert not re.search(r"<[A-Z][A-Z0-9_]*>", target_input["question"])
    assert set(target_input) == {"question"}
    assert any(parameter["type"] == "identifier" for parameter in orchestrator_only["parameters"])
    assert "reference_sql" not in target_input
    assert "result_contract" not in target_input
    assert len(evaluator_only["reference_sql"]) == evaluator_only["expected_statement_count"]
    assert evaluator_only["result_contract"]["order_sensitive"] is True
    for relative in evaluator_only["reference_sql"]:
        assert (ROOT / relative).is_file()


def test_blank_context_transcript_is_fresh_and_gold_free() -> None:
    transcript = load_yaml(TRANSCRIPT)
    assertions = transcript["initial_context_assertions"]
    assert transcript["executed"] is False
    assert all(value == "absent" for value in assertions.values())

    messages = transcript["messages"]
    assert [message["sequence"] for message in messages] == list(range(len(messages)))
    q01 = json.loads(QUESTIONS.read_text().strip())
    assert messages[0]["content_ref"] == "runner/prompts/native-agent-system.md"
    assert (ROOT / messages[0]["content_ref"]).is_file()
    assert messages[1]["content"] == q01["target_input"]["question"]
    tool_calls = [message["tool_call"]["name"] for message in messages if "tool_call" in message]
    assert tool_calls == [
        "db.list_relations",
        "db.describe_relations",
        "db.execute_readonly",
        "benchmark.submit_result",
    ]
    serialized = json.dumps(transcript).lower()
    assert "select " not in serialized
    assert "reference_sql" not in serialized
