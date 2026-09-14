import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SELECTION_PATH = ROOT / "benchmark/tpcds/features/representative-v1/selection.json"
CANONICAL_PATH = ROOT / "benchmark/tpcds/questions/canonical/questions.jsonl"


def _canonical_questions() -> dict[str, dict]:
    return {
        record["id"]: record
        for line in CANONICAL_PATH.read_text().splitlines()
        if line.strip()
        for record in [json.loads(line)]
    }


def test_representative_suite_is_a_non_official_12_question_selection() -> None:
    selection = json.loads(SELECTION_PATH.read_text())
    questions = selection["questions"]

    assert selection["status"] == "manual_selection"
    assert selection["official_tpcds_selection"] is False
    assert len(questions) == selection["selection_policy"]["target_size"] == 12
    assert len({question["id"] for question in questions}) == len(questions)
    assert "not a benchmark score" in selection["publication_scope"]


def test_selection_preserves_canonical_source_identity() -> None:
    selection = json.loads(SELECTION_PATH.read_text())
    canonical = _canonical_questions()

    for selected in selection["questions"]:
        source = canonical[selected["id"]]
        assert selected["source_template"] == source["source_template"]
        assert selected["source_multi_statement"] is source["multi_statement"]
        assert selected["reference_sql_files"] == source["reference_sql"]["local_files"]
        assert all((ROOT / path).is_file() for path in selected["reference_sql_files"])
        assert selected["rationale_en"] and selected["rationale_zh_cn"]

        multi = "multi_formulation" in selected["capabilities"]
        assert multi is source["multi_statement"]
        if multi:
            assert len(selected["reference_sql_files"]) > 1


def test_selection_covers_every_declared_capability() -> None:
    selection = json.loads(SELECTION_PATH.read_text())
    vocabulary = set(selection["capabilities"])
    declared = set(selection["coverage_requirements"])
    observed = {
        capability
        for question in selection["questions"]
        for capability in question["capabilities"]
    }

    assert declared == vocabulary
    assert observed >= declared
    assert all(set(question["capabilities"]) <= vocabulary for question in selection["questions"])
    assert {"q14", "q39"} <= {question["id"] for question in selection["questions"]}


def test_representative_suite_readmes_use_english_default() -> None:
    directory = SELECTION_PATH.parent
    english = (directory / "README.md").read_text()
    chinese = (directory / "README.zh-CN.md").read_text()
    switcher = "[English](README.md) | [简体中文](README.zh-CN.md)"

    assert english.startswith("# TPC-DS representative semantic suite v1")
    assert chinese.startswith("# TPC-DS 代表性语义题集 v1")
    assert switcher in english
    assert switcher in chinese
