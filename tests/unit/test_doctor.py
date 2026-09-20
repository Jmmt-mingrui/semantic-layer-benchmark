from __future__ import annotations

import json
from pathlib import Path

from runner.cli import main
from runner.core.doctor import diagnose


ROOT = Path(__file__).resolve().parents[2]


def test_doctor_distinguishes_installation_from_runtime_assets(monkeypatch) -> None:
    for name in (
        "BENCHMARK_DATABASE_URL",
        "BENCHMARK_AGENT_PROVIDER",
        "BENCHMARK_AGENT_MODEL",
        "BENCHMARK_AGENT_ENDPOINT",
        "BENCHMARK_AGENT_API_KEY_ENV",
    ):
        monkeypatch.delenv(name, raising=False)

    report = diagnose(ROOT)

    assert report["installation_ready"] is True
    assert report["live_run_ready"] is False
    assert report["status"] == "installation_ok"
    assert next(item for item in report["checks"] if item["name"] == "duckdb")["status"] == "ok"


def test_doctor_cli_default_succeeds_but_strict_reports_missing_assets(capsys) -> None:
    assert main(["doctor", "--root", str(ROOT)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["installation_ready"] is True

    assert main(["doctor", "--root", str(ROOT), "--strict"]) == 2


def test_doctor_rejects_an_incomplete_database(monkeypatch, tmp_path) -> None:
    database = tmp_path / "incomplete.duckdb"
    import duckdb

    connection = duckdb.connect(str(database))
    connection.execute("create table only_one_table(id integer)")
    connection.close()
    monkeypatch.setenv("BENCHMARK_DATABASE_URL", f"duckdb:///{database}")

    report = diagnose(ROOT)
    check = next(item for item in report["checks"] if item["name"] == "sf1_database")

    assert check["status"] == "error"
    assert "expected 25" in check["detail"]
