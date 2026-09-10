from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import duckdb
import yaml

from runner.core.agent import AgentTurn, AgentUsage, ScriptedAgentProvider, ToolCall
from runner.core.control_runner import run_control_experiment
from scripts.load_tpcds_sf1 import TABLES


ROOT = Path(__file__).parents[2]


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _manifest(path: Path, database_path: Path, dataset_sha: str) -> None:
    tables = {
        name: {"source": f"generated/{name}.dat", "rows": 0, "sha256": f"{index + 1:064x}"}
        for index, name in enumerate(TABLES)
    }
    path.write_text(
        json.dumps(
            {
                "schema_version": "0.1.0",
                "benchmark": "TPC-DS-derived",
                "scale_factor": 1,
                "generator": {"name": "dsdgen", "version": "4.0.0", "binary_sha256": None},
                "engine": {"name": "duckdb", "version": "1.4.0"},
                "schema": {"path": "schema.sql", "sha256": "a" * 64},
                "database": {"path": str(database_path), "sha256": _sha(database_path)},
                "tables": tables,
                "dataset_sha256": dataset_sha,
                "generated_at": "2026-09-10T00:00:00Z",
                "elapsed_ms": 1.0,
            }
        )
    )


def _question(path: Path, reference_sql: Path) -> None:
    record = {
        "schema_version": "0.1.0",
        "instance_id": "q01-control-test",
        "question_id": "q01",
        "source_template": "query1.tpl",
        "target_input": {"question": "Return the available IDs in ascending order."},
        "orchestrator_only": {"parameters": []},
        "evaluator_only": {
            "reference_sql": [str(reference_sql)],
            "expected_statement_count": 1,
            "result_contract": {
                "columns": ["id"],
                "order_sensitive": True,
                "max_rows": 100,
                "comparison": "exact_normalized",
            },
        },
    }
    path.write_text(json.dumps(record) + "\n")


def _provider(target: str) -> ScriptedAgentProvider:
    calls = []
    if target == "blank_context":
        calls.extend(
            [
                AgentTurn(tool_calls=(ToolCall("list", "db.list_relations", {"schema": "main"}),)),
                AgentTurn(tool_calls=(ToolCall("describe", "db.describe_relations", {"relations": ["sample"]}),)),
            ]
        )
    calls.extend(
        [
            AgentTurn(
                tool_calls=(ToolCall("execute", "db.execute_readonly", {"sql": "SELECT id FROM sample ORDER BY id"}),),
                usage=AgentUsage(10, 5, 0),
                response_id=f"{target}-execute",
            ),
            AgentTurn(
                tool_calls=(ToolCall("submit", "benchmark.submit_result", {"status": "success", "result_handles": ["result-001"]}),),
                usage=AgentUsage(10, 5, 0),
                response_id=f"{target}-submit",
            ),
        ]
    )
    return ScriptedAgentProvider(calls)


def test_control_runner_keeps_blank_context_empty_and_scores_both_controls(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "control.duckdb"
    with duckdb.connect(str(database_path)) as database:
        database.execute("CREATE TABLE sample(id INTEGER)")
        database.execute("INSERT INTO sample VALUES (2), (1)")
    reference_sql = tmp_path / "reference.sql"
    reference_sql.write_text("SELECT id FROM sample ORDER BY id\n")
    question_path = tmp_path / "questions.jsonl"
    _question(question_path, reference_sql)
    dataset_sha = "d" * 64
    manifest_path = tmp_path / "manifest.json"
    _manifest(manifest_path, database_path, dataset_sha)

    database_config = tmp_path / "database.yaml"
    database_config.write_text(
        yaml.safe_dump(
            {
                "connection": {"driver": "duckdb", "url": {"env": "TEST_DATABASE_URL"}, "read_only": True},
                "namespace": {"catalog": {"env": "TEST_DATABASE_CATALOG", "default": None}, "schema": {"env": "TEST_DATABASE_SCHEMA", "default": "main"}},
            }
        )
    )
    config = yaml.safe_load((ROOT / "runner/config/control-sf1-q01.yaml").read_text())
    config["workload"]["question_instances"] = str(question_path)
    config["dataset"]["manifest"] = str(manifest_path)
    config["dataset"]["database_config"] = str(database_config)
    config["execution"]["repetitions"] = 1
    config["execution"]["target_order"] = "fixed"
    config["execution"]["question_order"] = "fixed"
    config["artifacts"]["run_directory"] = str(tmp_path / "runs")
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))

    monkeypatch.setenv("TEST_DATABASE_URL", f"duckdb://{database_path}")
    monkeypatch.setenv("BENCHMARK_DATASET_SHA256", dataset_sha)
    monkeypatch.setenv("BENCHMARK_AGENT_PROVIDER", "scripted")
    monkeypatch.setenv("BENCHMARK_AGENT_MODEL", "contract-test")

    providers: list[tuple[str, ScriptedAgentProvider]] = []

    def factory(target: str, repetition: int, question: dict) -> ScriptedAgentProvider:
        assert repetition == 1
        assert question["question_id"] == "q01"
        provider = _provider(target)
        providers.append((target, provider))
        return provider

    run_path = run_control_experiment(config_path, factory, root=ROOT)
    run = json.loads(run_path.read_text())
    assert run["summary"] == {
        "planned": 2,
        "completed": 2,
        "passed": 2,
        "failed": 0,
        "unsupported": 0,
        "invalid": 0,
        "timeout": 0,
    }
    assert run["status"] == "completed"
    assert len({id(provider) for _, provider in providers}) == 2

    trials = [json.loads(Path(path).read_text()) for path in run["trial_records"]]
    by_target = {trial["condition"]["target"]: trial for trial in trials}
    assert by_target["blank_context"]["condition"]["artifact_sha256"] is None
    assert by_target["ddl_only"]["condition"]["artifact_sha256"] is not None
    assert all(trial["evaluation"]["result_equivalent"] is True for trial in trials)

    blank_transcript = [
        json.loads(line)
        for line in Path(by_target["blank_context"]["conversation"]["sanitized_transcript"]).read_text().splitlines()
    ]
    assert [message["role"] for message in blank_transcript[:2]] == ["system", "user"]
    assert "CREATE TABLE" not in json.dumps(blank_transcript[:2])

    ddl_transcript = [
        json.loads(line)
        for line in Path(by_target["ddl_only"]["conversation"]["sanitized_transcript"]).read_text().splitlines()
    ]
    assert [message["role"] for message in ddl_transcript[:3]] == ["system", "system", "user"]
    assert "create table" in ddl_transcript[1]["content"].lower()
