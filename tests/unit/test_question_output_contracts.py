from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import duckdb
import pytest

from runner.core.control_tools import result_sha256
from runner.core.database import QueryResult
from runner.core.local_live import render_report, summarize_outcomes
from runner.core.question_contracts import (
    QuestionContractError, render_output_requirements, statement_contracts,
    validate_reference_contract, validate_result_contract,
)
from runner.core.representative_gold import RepresentativeGoldError, load_representative_instances
from scripts.benchmark_lint import validate_question_output_contracts
from scripts.materialize_representative_questions import INSTANCES, SPECS, representative_instances


ROOT = Path(__file__).resolve().parents[2]


def _write_instances(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "instances.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return path


def _replace_requirements(row: dict) -> None:
    row["target_input"]["question"] = "Test business question. " + render_output_requirements(statement_contracts(row))


def test_all_twelve_public_contracts_are_reviewable_reproducible_and_bound_to_sql():
    rows = load_representative_instances(ROOT / INSTANCES)
    assert rows == representative_instances()
    validate_question_output_contracts(ROOT)
    assert sum(len(statement_contracts(row)) for row in rows) == 14
    for row in rows:
        assert set(row["target_input"]) == {"question"}
        assert "benchmark/tpcds/" not in row["target_input"]["question"]
        assert "sha256" not in row["target_input"]["question"]
        assert "<" not in row["target_input"]["question"]
        assert all(contract["order_sensitive"] for contract in statement_contracts(row))


def test_q01_qualification_and_representative_questions_are_identical():
    qualification = json.loads((ROOT / "benchmark/tpcds/questions/instances/sf1-qualification-q01.jsonl").read_text())
    question = representative_instances()[0]["target_input"]["question"]
    assert question == qualification["target_input"]["question"]
    assert "that same store" in question
    assert "c_customer_id ASC NULLS LAST" in question
    assert "up to 100" in question
    assert "do not deduplicate" in question


@pytest.mark.parametrize("field", ["columns", "order_sensitive", "max_rows", "comparison", "order_by"])
def test_missing_contract_fields_fail_closed(tmp_path, field):
    rows = deepcopy(representative_instances())
    del rows[0]["evaluator_only"]["result_contract"][field]
    with pytest.raises(RepresentativeGoldError, match="invalid question contract"):
        load_representative_instances(_write_instances(tmp_path, rows))


def test_old_underdefined_schema_is_rejected(tmp_path):
    rows = deepcopy(representative_instances())
    rows[0]["schema_version"] = "0.2.0"
    with pytest.raises(RepresentativeGoldError, match="invalid question contract"):
        load_representative_instances(_write_instances(tmp_path, rows))


def test_metadata_alone_is_not_sufficient_the_agent_must_see_the_requirements(tmp_path):
    rows = deepcopy(representative_instances())
    rows[0]["target_input"]["question"] = SPECS["q01"]["question"]
    with pytest.raises(RepresentativeGoldError, match="complete public output requirements"):
        load_representative_instances(_write_instances(tmp_path, rows))


@pytest.mark.parametrize("question_id, name, value", [
    ("q01", "YEAR", True), ("q05", "START_DATE", "not-a-date"),
    ("q03", "MANUFACTURER_ID", "128"),
])
def test_materialization_values_are_actually_typed(tmp_path, question_id, name, value):
    rows = deepcopy(representative_instances())
    row = next(row for row in rows if row["question_id"] == question_id)
    parameter = next(parameter for parameter in row["orchestrator_only"]["parameters"] if parameter["name"] == name)
    parameter["value"] = value
    with pytest.raises(RepresentativeGoldError, match="must have type"):
        load_representative_instances(_write_instances(tmp_path, rows))


@pytest.mark.parametrize("change, message", [
    ("columns", "Reference columns differ"), ("direction", "ORDER BY differs"),
    ("nulls", "ORDER BY differs"), ("limit", "LIMIT differs"),
    ("unlimited", "LIMIT differs"), ("missing_sort", "ORDER BY differs"),
])
def test_public_and_reference_output_rules_cannot_drift(tmp_path, change, message):
    rows = deepcopy(representative_instances())
    contract = rows[0]["evaluator_only"]["result_contract"]
    if change == "columns":
        contract["columns"] = ["customer_id"]
        contract["order_by"][0]["column"] = "customer_id"
    elif change == "direction":
        contract["order_by"][0]["direction"] = "DESC"
    elif change == "nulls":
        contract["order_by"][0]["nulls"] = "FIRST"
    elif change == "limit":
        contract["max_rows"] = 50
    elif change == "unlimited":
        contract["max_rows"] = None
    else:
        rows[0]["evaluator_only"]["reference_sql"] = [str(tmp_path / "no-sort.sql")]
        (tmp_path / "no-sort.sql").write_text("SELECT c_customer_id FROM customer LIMIT 100")
    _replace_requirements(rows[0])
    with pytest.raises(RepresentativeGoldError, match=message):
        load_representative_instances(_write_instances(tmp_path, rows))


def test_both_multi_statement_contracts_are_checked_in_submission_order(tmp_path):
    rows = deepcopy(representative_instances())
    row = next(row for row in rows if row["question_id"] == "q14")
    row["evaluator_only"]["result_contract"]["statements"].reverse()
    _replace_requirements(row)
    with pytest.raises(RepresentativeGoldError, match="q14: Reference columns differ"):
        load_representative_instances(_write_instances(tmp_path, rows))


def test_contracts_cannot_silently_relax_strict_normalization(tmp_path):
    rows = deepcopy(representative_instances())
    rows[0]["evaluator_only"]["result_contract"]["order_sensitive"] = False
    with pytest.raises(RepresentativeGoldError, match="invalid question contract"):
        load_representative_instances(_write_instances(tmp_path, rows))


@pytest.mark.parametrize("change", ["columns", "limit", "comparison", "order_sensitive", "normalization_revision"])
def test_gold_must_obey_the_reviewed_output_contract(change):
    contract = representative_instances()[0]["evaluator_only"]["result_contract"]
    result = {"columns": ["c_customer_id"], "row_count": 1, "comparison": "exact_normalized",
              "order_sensitive": True, "normalization_revision": "canonical-json-v1"}
    result[{"limit": "row_count"}.get(change, change)] = {
        "columns": ["id"], "limit": 101, "comparison": "numeric_tolerance", "order_sensitive": False,
        "normalization_revision": "different-v1",
    }[change]
    with pytest.raises(QuestionContractError):
        validate_result_contract(result, contract)


def test_strict_hash_still_includes_column_names_column_order_and_row_order():
    result = QueryResult(("id", "total"), [(1, 10), (2, 20)], 0)
    hash_value = result_sha256(result)
    assert hash_value != result_sha256(QueryResult(("total", "id"), [(10, 1), (20, 2)], 0))
    assert hash_value != result_sha256(QueryResult(("customer_id", "total"), result.rows, 0))
    assert hash_value != result_sha256(QueryResult(result.columns, list(reversed(result.rows)), 0))


def test_inner_sort_or_limit_cannot_substitute_for_outer_requirements():
    contract = representative_instances()[0]["evaluator_only"]["result_contract"]
    with duckdb.connect(":memory:") as database:
        with pytest.raises(QuestionContractError, match="outer ORDER BY"):
            validate_reference_contract(database, "SELECT * FROM (SELECT 'id' AS c_customer_id ORDER BY c_customer_id LIMIT 100)", contract)


def test_six_attempts_with_gateway_failures_are_not_reported_as_six_wrong_answers():
    rows = [{"question_id": "q01", "question": "Question", "target": "blank_context", "status": "failed",
             "result_equivalent": False} for _ in range(2)]
    rows += [{"question_id": "q02", "question": "Question", "target": "blank_context", "status": "timeout",
              "result_equivalent": None, "error": "Agent exhausted max_turns"}]
    rows += [{"question_id": "q03", "question": "Question", "target": "ddl_only", "status": "failed",
              "result_equivalent": None, "error": "LiveProviderError: provider HTTP error 403"} for _ in range(3)]
    counts = summarize_outcomes(rows)
    assert counts == {"attempted": 6, "scored_submissions": 2, "correct_submissions": 0, "wrong_results": 2,
                      "unscored": 4, "provider_errors": 3, "submitted_result_match_rate": 0,
                      "publishable_execution_accuracy": None}
    report = render_report(rows)
    assert "提交并参与 Gold 比对 2 次" in report
    assert "供应商/API 错误 3 次" in report
    assert "完整 benchmark" in report
    assert summarize_outcomes([])["submitted_result_match_rate"] is None


def test_q02_public_aliases_preserve_original_ratio_and_date_pair_multiplicity():
    """Tiny synthetic fixture, not real SF1 or a model-accuracy result."""
    with duckdb.connect(":memory:") as database:
        database.execute((ROOT / "data/tpcds/schema/duckdb/schema.sql").read_text())
        database.execute("""
            INSERT INTO date_dim(d_date_sk,d_date_id,d_year,d_week_seq,d_day_name) VALUES
              (1,'D1',2001,100,'Sunday'),(2,'D2',2001,100,'Monday'),
              (3,'D3',2002,153,'Sunday'),(4,'D4',2002,153,'Monday');
            INSERT INTO web_sales(ws_item_sk,ws_order_number,ws_sold_date_sk,ws_ext_sales_price) VALUES
              (1,1,1,10),(1,2,2,10),(1,3,3,20),(1,4,4,40);
            INSERT INTO catalog_sales(cs_item_sk,cs_order_number,cs_sold_date_sk,cs_ext_sales_price) VALUES
              (1,1,1,20),(1,3,3,40);
        """)
        old = database.execute((ROOT / "benchmark/tpcds/sql/reference/postgres/query02.sql").read_text()).fetchall()
        cursor = database.execute((ROOT / "benchmark/tpcds/sql/reference/duckdb/query02.sql").read_text())
        assert [column[0] for column in cursor.description] == SPECS["q02"]["contracts"][0]["columns"]
        new = cursor.fetchall()
        assert new == old == [(100, 0.5, 0.25, None, None, None, None, None)] * 4


@pytest.mark.parametrize("part", [1, 2])
def test_q39_public_aliases_preserve_both_formulations_on_nonempty_inventory(part):
    with duckdb.connect(":memory:") as database:
        database.execute((ROOT / "data/tpcds/schema/duckdb/schema.sql").read_text())
        database.execute("""
            INSERT INTO warehouse(w_warehouse_sk,w_warehouse_id,w_warehouse_name) VALUES (1,'W1','Warehouse');
            INSERT INTO item(i_item_sk,i_item_id) VALUES (1,'I1');
            INSERT INTO date_dim(d_date_sk,d_date_id,d_year,d_moy) VALUES
              (1,'D1',2001,1),(2,'D2',2001,1),(3,'D3',2001,1),
              (4,'D4',2001,2),(5,'D5',2001,2),(6,'D6',2001,2);
            INSERT INTO inventory(inv_date_sk,inv_item_sk,inv_warehouse_sk,inv_quantity_on_hand) VALUES
              (1,1,1,0),(2,1,1,0),(3,1,1,30),(4,1,1,0),(5,1,1,0),(6,1,1,60);
        """)
        old = database.execute((ROOT / f"benchmark/tpcds/sql/reference/postgres/query39_{part}.sql").read_text()).fetchall()
        cursor = database.execute((ROOT / f"benchmark/tpcds/sql/reference/duckdb/query39_{part}.sql").read_text())
        assert [column[0] for column in cursor.description] == SPECS["q39"]["contracts"][part - 1]["columns"]
        new = cursor.fetchall()
        assert new == old and len(new) == 1
        assert new[0][3] == 10 and new[0][8] == 20 and new[0][4] > 1.5
