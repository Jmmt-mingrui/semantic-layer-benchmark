"""Regression cases for the attached audit; synthetic protocol tests, not benchmark scores."""
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from runner.core.agent import AgentTurn, ScriptedAgentProvider, ToolCall
from runner.core.control_runner import _provider_messages, _redact_persisted_transcript
from runner.core.control_tools import result_sha256
from runner.core.database import QueryResult
from runner.core.native_adapter import NativeResponse
from runner.core.native_runner import run_native_trial
from runner.core.okf_native_consumer import OkfNativeConsumer
from runner.core.publication_orchestrator import materialize_publication_trial
from tests.unit.test_native_runner import _factory, _settings, _question, ROOT
from tests.unit.test_okf_native_consumer import _target, _write_bundle
from tests.unit.test_publication_orchestrator import _candidate, _gold, _trace, CONTRACTS
from runner.core.local_live import load_env_file, render_report


def test_explorations_are_not_answers_and_submitted_order_is_preserved(tmp_path):
    class Database:
        settings = SimpleNamespace(schema="main")

        def execute(self, sql, parameters=()):
            return QueryResult(("id",), [(int(sql.rsplit(" ", 1)[-1]),)], 0.1)

    factory = _factory(tmp_path)
    factory.database = Database()
    turns = [AgentTurn(tool_calls=(ToolCall(str(i), "db.execute_readonly", {"sql": f"SELECT {i}"}),)) for i in range(1, 4)]
    turns.append(AgentTurn(tool_calls=(ToolCall("submit", "benchmark.submit_result", {"status": "success", "result_handles": ["result-003", "result-001"]}),)))
    outcome = run_native_trial(target="ddl_only", question_instance=_question(), repetition=1,
        adapter_factory=factory, provider_factory=lambda *unused: ScriptedAgentProvider(turns),
        settings=replace(_settings(), max_turns=4, capture_details=True), system_prompt="isolated")
    assert outcome.record["status"] == "candidate_ready"
    artifacts = outcome.record["candidate"]["result_artifacts"]
    assert [a["result_handle"] for a in artifacts] == ["result-003", "result-001"]
    assert artifacts[0]["result_sha256"] == result_sha256(QueryResult(("id",), [(3,)], 0))
    assert len(outcome.details["queries"]) == 3
    assert [q["submitted"] for q in outcome.details["queries"]] == [True, False, True]
    assert outcome.record["conversation"]["tool_schema_sha256"] != __import__('hashlib').sha256(b'[]').hexdigest()
    assert "SELECT 3" not in json.dumps(outcome.record)


def test_failed_preflight_is_closed_and_materializable(tmp_path):
    factory = _factory(tmp_path)
    runtime = factory.create("okf")
    runtime.preflight = lambda timeout: (NativeResponse("error", 0, {"error": "bad native config"}),)
    factory.create = lambda target: runtime
    outcome = run_native_trial(target="okf", question_instance=_question(), repetition=1,
        adapter_factory=factory, provider_factory=lambda *unused: pytest.fail("provider must not start"),
        settings=_settings(), system_prompt="isolated")
    assert runtime._closed
    assert outcome.record["error"]["category"] == "preflight"
    assert "bad native config" in outcome.record["error"]["detail"]
    assert outcome.record["conversation"]["provider_closed_before_evaluation"]
    candidate = _candidate()
    candidate.update(status="invalid", provider={"kind": "unavailable", "ranking_eligible": False},
        error=outcome.record["error"])
    candidate["conversation"].update(message_count=0, message_manifest=[], provider_response_ids=[])
    candidate["candidate"] = {"result_artifacts": [], "sql_artifacts": []}
    record = materialize_publication_trial(run_id="run", experiment_id="representative-v1", lane="native_end_to_end",
        candidate=candidate, native_trace=_trace(), gold=_gold(), output_dir=tmp_path, contracts_dir=CONTRACTS)
    assert record["status"] == "invalid"
    assert record["evaluation"]["result_equivalent"] is None
    assert "bad native config" in record["evaluation"]["error_detail"]


def test_directory_links_work_and_escape_is_still_rejected(tmp_path):
    root = tmp_path / "bundle"
    _write_bundle(root)
    (root / "index.md").write_text("---\ntitle: Index\n---\n[Tables](tables/)\n")
    consumer = OkfNativeConsumer(root, _target())
    assert consumer.validate_links()["checked_links"] == 1
    assert consumer.follow_link("index.md", "tables/")["files"][0]["path"] == "tables/table.md"
    (root / "escape").symlink_to(tmp_path, target_is_directory=True)
    (root / "index.md").write_text("---\ntitle: Index\n---\n[Escape](escape/)\n")
    with pytest.raises(Exception, match="outside|Symlinks"):
        consumer.validate_links()


def test_control_wire_format_does_not_break_preview_redaction():
    messages = [{"role": "assistant", "tool_calls": [{"id": "x", "name": "db.execute_readonly", "arguments": {"sql": "SELECT 1"}}]},
                {"role": "tool", "tool_call_id": "x", "content": {"preview_rows": [[1]]}}]
    wire = _provider_messages(messages)
    assert wire[0]["tool_calls"][0]["type"] == "function"
    assert json.loads(wire[0]["tool_calls"][0]["function"]["arguments"])["sql"] == "SELECT 1"
    assert isinstance(wire[1]["content"], str)
    assert isinstance(messages[1]["content"], dict)
    assert _redact_persisted_transcript(messages)[1]["content"]["preview_rows"] == "[redacted_from_persisted_artifact]"


def test_dotenv_literal_only_and_existing_environment_wins(tmp_path, monkeypatch):
    path = tmp_path / ".env.local"
    path.write_text("EXAMPLE_VAR='literal $(not-executed)'\nEXISTING_VAR=new\n")
    monkeypatch.delenv("EXAMPLE_VAR", raising=False)
    monkeypatch.setenv("EXISTING_VAR", "old")
    load_env_file(path)
    import os
    assert os.environ["EXAMPLE_VAR"] == "literal $(not-executed)"
    assert os.environ["EXISTING_VAR"] == "old"


def test_readable_report_distinguishes_execution_from_correctness():
    report = render_report([{"question_id": "q01", "question": "Test question", "target": "ddl_only", "status": "failed",
        "result_equivalent": False, "details": {"queries": [{"submitted": True, "sql": "SELECT 1", "row_count": 1, "preview": {"columns": ["id"], "rows": [[1]]}}]}}])
    assert "不一致" in report and "SELECT 1" in report and "提交答案" in report


def test_metricflow_models_use_the_duckdb_namespace():
    import yaml
    directory = ROOT / "semantic-models/metricflow/tpcds-sf1"
    for path in (directory / "semantic_models").glob("*.yml"):
        model = yaml.safe_load(path.read_text())["semantic_model"]
        assert model["node_relation"]["schema_name"] == "main"
        assert model["node_relation"]["database"] == "tpcds"
        assert "to_date(" not in path.read_text()


def test_all_metricflow_expressions_bind_against_duckdb_schema():
    import duckdb, yaml
    with duckdb.connect(":memory:") as database:
        database.execute((ROOT / "data/tpcds/schema/duckdb/schema.sql").read_text())
        for path in (ROOT / "semantic-models/metricflow/tpcds-sf1/semantic_models").glob("*.yml"):
            model = yaml.safe_load(path.read_text())["semantic_model"]
            table = model["node_relation"]["alias"]
            for group in ("entities", "dimensions", "measures"):
                for entry in model.get(group, []):
                    if entry.get("expr"):
                        database.execute(f'SELECT {entry["expr"]} FROM "{table}" LIMIT 0')
        assert str(database.execute("SELECT DATE '1970-01-01' + CAST(2450815 - 2440588 AS INTEGER)").fetchone()[0]) == "1998-01-01"


def test_local_live_end_to_end_report_with_protocol_fixture(tmp_path, monkeypatch):
    """Mock provider/Gold gates for protocol verification, never real model accuracy."""
    import duckdb
    import yaml
    import runner.core.local_live as local
    from runner.cli import build_parser
    database = tmp_path / "sample.duckdb"
    with duckdb.connect(str(database)) as db:
        db.execute("CREATE TABLE sample(id INTEGER); INSERT INTO sample VALUES (7)")
    config = tmp_path / "database.yaml"
    config.write_text(yaml.safe_dump({"connection": {"driver": "duckdb", "url": {"env": "LOCAL_TEST_DB", "default": f"duckdb://{database}"}, "read_only": True},
        "namespace": {"catalog": {"env": "LOCAL_TEST_CATALOG", "default": None}, "schema": {"env": "LOCAL_TEST_SCHEMA", "default": "main"}}}))
    instances_path = ROOT / "benchmark/tpcds/questions/instances/sf1-representative-v1.jsonl"
    questions = [json.loads(line) for line in instances_path.read_text().splitlines()]
    selected = {q["question_id"]: q for q in questions if q["question_id"] in {"q01", "q02", "q03"}}
    pack = tmp_path / "pack.json"
    pack.write_text(json.dumps({"instances_path": str(instances_path), "gold": [{"question_id": q, "path": str(tmp_path / (q + '.json'))} for q in selected]}))
    monkeypatch.setattr(local, "verify_representative_pack", lambda **unused: {"test_fixture": True, "ranking_eligible": False})
    answer_hash = result_sha256(QueryResult(("id",), [(7,)], 0))
    monkeypatch.setattr(local, "load_gold_for_candidate", lambda candidate, **unused: ({
        "question_id": candidate["question"]["question_id"], "instance_id": candidate["question"]["instance_id"],
        "statements": [{"result": {"sha256": answer_hash}}]}, {}))
    class FixtureProvider(ScriptedAgentProvider):
        # Test-only stub satisfies materializer's live contract; output is explicitly nonpublishable.
        provider_kind = "live"
        ranking_eligible = True
        def __init__(self, settings):
            super().__init__([AgentTurn(tool_calls=(ToolCall("explore", "db.execute_readonly", {"sql": "SELECT 99 AS id"}),), response_id="fixture-explore"),
                AgentTurn(tool_calls=(ToolCall("answer", "db.execute_readonly", {"sql": "SELECT id FROM sample"}),), response_id="fixture-answer"),
                AgentTurn(tool_calls=(ToolCall("submit", "benchmark.submit_result", {"status": "success", "result_handles": ["result-002"]}),), response_id="fixture-submit")])
    monkeypatch.setattr(local, "LiveAgentProvider", FixtureProvider)
    monkeypatch.setenv("BENCHMARK_AGENT_PROVIDER", "protocol-fixture")
    monkeypatch.setenv("BENCHMARK_AGENT_MODEL", "not-a-real-model")
    monkeypatch.setenv("BENCHMARK_AGENT_ENDPOINT", "http://localhost/v1")
    monkeypatch.delenv("BENCHMARK_AGENT_API_KEY_ENV", raising=False)
    output = tmp_path / "output"
    args = build_parser().parse_args(["run-live", "--root", str(ROOT), "--questions", "q01", "q02", "q03",
        "--targets", "ddl_only", "--database-config", str(config), "--gold-pack", str(pack),
        "--output", str(output), "--save-details"])
    assert local.run_local_live(args) == 0
    summary = json.loads((output / "summary.json").read_text())
    assert summary["publishable"] is False
    assert len(summary["trials"]) == 3
    assert all(t["result_equivalent"] is True for t in summary["trials"])
    assert "SELECT id FROM sample" in (output / "REPORT.zh-CN.md").read_text()
    assert "探索查询" in (output / "REPORT.zh-CN.md").read_text()


def test_generator_uses_short_parser_arguments_in_deep_paths(tmp_path, monkeypatch):
    import scripts.generate_tpcds_sf1 as generator
    binary = tmp_path / "tools" / "dsdgen"
    binary.parent.mkdir()
    binary.write_text("test binary")
    (binary.parent / "tpcds.idx").write_text("test distributions")
    output = tmp_path / ("nested" * 20) / "generated"
    def run(argv, **kwargs):
        assert argv[argv.index("-dir") + 1] == "."
        assert argv[argv.index("-distributions") + 1] == "tpcds.idx"
        Path(kwargs["cwd"], "sample.dat").write_text("synthetic protocol fixture")
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(generator.subprocess, "run", run)
    monkeypatch.setattr("sys.argv", ["generate_tpcds_sf1", "--dsdgen", str(binary), "--output", str(output)])
    assert generator.main() == 0
    assert (output / "sample.dat").is_file()
