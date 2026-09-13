from __future__ import annotations

from pathlib import Path

import pytest

from runner.adapters.skill_host import (
    SkillHostAdapter,
    SkillPackageError,
    SkillStateError,
)
from runner.core.native_adapter import NativeIsolationError, NativeRequest


TARGET = {
    "allowed_operations": [
        "skill.activate",
        "skill.read_instruction",
        "skill.read_reference",
        "db.execute_readonly",
        "benchmark.submit_result",
    ],
    "prohibited_operations": [
        "skill.preload_all_references",
        "semantic.normalized_chunks",
        "benchmark.read_gold",
    ],
}


def make_package(tmp_path: Path) -> Path:
    root = tmp_path / "tpcds-sf1-table-semantics"
    references = root / "references"
    references.mkdir(parents=True)
    (root / "SKILL.md").write_text(
        "---\nname: tpcds-sf1-table-semantics\ndescription: Native package.\n---\n\n# Instructions\n",
        encoding="utf-8",
    )
    (references / "schema.md").write_text("# Schema\n", encoding="utf-8")
    return root


def request(operation: str, arguments: dict[str, object] | None = None) -> NativeRequest:
    return NativeRequest(operation=operation, arguments=arguments or {}, deadline_seconds=2)


def test_discovery_is_metadata_only_and_activation_is_explicit(tmp_path: Path) -> None:
    adapter = SkillHostAdapter(make_package(tmp_path), TARGET, host_revision="host-2026-09-13")

    tools = adapter.public_tools()
    assert {tool["name"] for tool in tools} == {"skill.activate", "skill.read_reference"}
    assert "Instructions" not in repr(tools)
    assert adapter.access_telemetry == ()
    assert adapter.identity.name == "tpcds-sf1-table-semantics"

    with pytest.raises(SkillStateError, match="Activate"):
        adapter.dispatch(request("skill.read_reference", {"path": "references/schema.md"}))

    result = adapter.dispatch(request("skill.activate"))
    assert result.output["instruction"].endswith("# Instructions\n")
    assert result.output["identity"]["host_revision"] == "host-2026-09-13"
    assert [event["operation"] for event in adapter.access_telemetry] == ["skill.activate"]


def test_reads_only_one_requested_reference_and_records_sanitized_access(tmp_path: Path) -> None:
    adapter = SkillHostAdapter(make_package(tmp_path), TARGET, host_revision="host-a")
    adapter.dispatch(request("skill.activate"))

    response = adapter.dispatch(request("skill.read_reference", {"path": "references/schema.md"}))

    assert response.output == {"path": "references/schema.md", "content": "# Schema\n"}
    telemetry = adapter.access_telemetry[-1]
    assert telemetry["path"] == "references/schema.md"
    assert telemetry["byte_count"] == len("# Schema\n".encode())
    assert telemetry["sha256"]
    assert "content" not in telemetry


@pytest.mark.parametrize("path", ["../SKILL.md", "/etc/passwd", "references/../../gold.json"])
def test_rejects_path_traversal_and_evaluator_access(tmp_path: Path, path: str) -> None:
    adapter = SkillHostAdapter(make_package(tmp_path), TARGET, host_revision="host-a")
    adapter.dispatch(request("skill.activate"))
    with pytest.raises(NativeIsolationError):
        adapter.dispatch(request("skill.read_reference", {"path": path}))


def test_rejects_symlinks_and_package_identity_drift(tmp_path: Path) -> None:
    root = make_package(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    (root / "references" / "escape.md").symlink_to(outside)
    with pytest.raises(SkillPackageError, match="symlink"):
        SkillHostAdapter(root, TARGET, host_revision="host-a")

    root = make_package(tmp_path / "second")
    adapter = SkillHostAdapter(root, TARGET, host_revision="host-a")
    (root / "references" / "schema.md").write_text("changed", encoding="utf-8")
    with pytest.raises(SkillPackageError, match="identity changed"):
        adapter.preflight(2)


def test_rejects_preload_gold_and_undeclared_fallbacks(tmp_path: Path) -> None:
    adapter = SkillHostAdapter(make_package(tmp_path), TARGET, host_revision="runtime", expected_host_revision="runtime")
    with pytest.raises(SkillPackageError, match="revision"):
        SkillHostAdapter(make_package(tmp_path / "other"), TARGET, host_revision="runtime", expected_host_revision="wrong")
    with pytest.raises(NativeIsolationError):
        adapter.dispatch(request("skill.preload_all_references"))
    with pytest.raises(NativeIsolationError):
        adapter.dispatch(request("benchmark.read_gold"))
    with pytest.raises(NativeIsolationError):
        adapter.dispatch(request("semantic.normalized_chunks"))
    with pytest.raises(Exception, match="Undeclared"):
        adapter.dispatch(request("db.list_relations"))
