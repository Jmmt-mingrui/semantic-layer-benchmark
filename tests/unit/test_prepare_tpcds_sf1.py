from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.prepare_tpcds_sf1 import main, require_repository_root


def test_requires_benchmark_repository_root(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Not a benchmark repository root"):
        require_repository_root(tmp_path)


def test_pipeline_uses_only_checked_in_stages(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "data/tpcds/schema/duckdb").mkdir(parents=True)
    (tmp_path / "data/tpcds/schema/duckdb/schema.sql").write_text("-- schema\n")
    instances = tmp_path / "benchmark/tpcds/questions/instances"
    instances.mkdir(parents=True)
    (instances / "sf1-representative-v1.jsonl").write_text("{}\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fixture'\nversion='0'\n")
    binary = tmp_path / "dsdgen"
    binary.write_text("#!/bin/sh\n")
    binary.chmod(0o755)

    manifest = tmp_path / "data/tpcds/sf1/manifests/duckdb-sf1.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "dataset_sha256": "d" * 64,
                "database": {"sha256": "b" * 64},
                "tables": {"customer": {"rows": 7}},
            }
        )
    )
    pack = tmp_path / "benchmark/tpcds/results/gold/sf1/representative-v1/pack.json"
    pack.parent.mkdir(parents=True)
    pack.write_text(
        json.dumps(
            {
                "question_count": 12,
                "statement_count": 14,
                "pack_identity_sha256": "g" * 64,
            }
        )
    )

    commands: list[list[str]] = []
    monkeypatch.setattr(
        "scripts.prepare_tpcds_sf1.run",
        lambda command, *, root: commands.append(list(command)),
    )
    assert main(["--root", str(tmp_path), "--dsdgen", str(binary)]) == 0

    modules = [command[2] for command in commands]
    assert modules == [
        "scripts.generate_tpcds_sf1",
        "scripts.load_tpcds_sf1",
        "scripts.freeze_representative_sf1",
        "scripts.freeze_representative_sf1",
        "scripts.benchmark_lint",
        "pytest",
    ]
    assert "--verify" in commands[3]
    assert "--basetemp" in commands[-1]
    basetemp = Path(commands[-1][commands[-1].index("--basetemp") + 1])
    assert basetemp.parent == tmp_path.parent
    assert not basetemp.exists()
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "ready"
    assert summary["gold_question_count"] == 12
    assert summary["total_rows"] == 7
