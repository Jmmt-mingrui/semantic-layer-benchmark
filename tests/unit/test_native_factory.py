from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from runner.core.native_factory import NativeAdapterFactory, NativeFactorySettings


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = yaml.safe_load((ROOT / "runner/config/targets.native.yaml").read_text(encoding="utf-8"))
TOOL_CATALOG = json.loads((ROOT / "runner/tools/blank-context.tools.json").read_text(encoding="utf-8"))


class NoQueryDatabase:
    settings = SimpleNamespace(schema="main")

    def execute(self, sql, parameters=None):  # pragma: no cover - must not be reached in these tests
        raise AssertionError(f"unexpected database execution: {sql} {parameters}")


def _factory(tmp_path: Path) -> NativeAdapterFactory:
    runtime = tmp_path / "metricflow-runtime"
    runtime.mkdir()
    return NativeAdapterFactory(
        root=ROOT,
        registry=REGISTRY,
        database=NoQueryDatabase(),
        tool_catalog=TOOL_CATALOG,
        settings=NativeFactorySettings(
            metricflow_runtime_project_dir=runtime,
            skill_host_revision="test-host-revision",
        ),
    )


def _names(runtime) -> set[str]:
    return {str(tool["name"]) for tool in runtime.public_tools()}


def test_factory_preserves_each_targets_native_allowlist(tmp_path: Path) -> None:
    factory = _factory(tmp_path)

    blank = factory.create("blank_context")
    ddl = factory.create("ddl_only")
    metricflow = factory.create("metricflow")
    ossie = factory.create("ossie")
    okf = factory.create("okf")
    skill = factory.create("skill")

    assert _names(blank) == {
        "db.list_relations",
        "db.describe_relations",
        "db.execute_readonly",
        "benchmark.submit_result",
    }
    assert _names(ddl) == {"db.execute_readonly", "benchmark.submit_result"}
    assert "store_sales" in (ddl.initial_context or "")
    assert _names(metricflow) == {
        "metricflow.list_metrics",
        "metricflow.list_dimensions",
        "metricflow.list_dimension_values",
        "metricflow.list_entities",
        "metricflow.query",
        "benchmark.submit_result",
    }
    assert not any(name.startswith("db.") for name in _names(metricflow))
    assert _names(ossie) == {
        "ossie.inspect_model",
        "ossie.read_native_yaml",
        "db.execute_readonly",
        "benchmark.submit_result",
    }
    assert _names(okf) == {
        "okf.list_files",
        "okf.read_file",
        "okf.follow_link",
        "okf.search_text",
        "db.execute_readonly",
        "benchmark.submit_result",
    }
    assert _names(skill) == {
        "skill.activate",
        "skill.read_reference",
        "db.execute_readonly",
        "benchmark.submit_result",
    }
    assert "skill_md_sha256" in (skill.initial_context or "")
    assert "SKILL.md" not in (skill.initial_context or "")

    for runtime in (blank, ddl, metricflow, ossie, okf, skill):
        assert "benchmark.read_gold" not in _names(runtime)
        runtime.close()
