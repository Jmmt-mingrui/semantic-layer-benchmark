from __future__ import annotations

from pathlib import Path

import pytest

from runner.core.native_adapter import NativeIsolationError, NativeRequest
from runner.core.okf_native_consumer import OkfBundleError, OkfNativeConsumer


def _target(root: str = "semantic-models/okf/tpcds-sf1") -> dict[str, object]:
    return {
        "native_surface": {"artifact_root": root},
        "allowed_operations": [
            "okf.validate_frontmatter",
            "okf.validate_links",
            "okf.list_files",
            "okf.read_file",
            "okf.follow_link",
            "okf.search_text",
        ],
        "prohibited_operations": ["semantic.normalized_chunks", "benchmark.read_gold"],
    }


def _write_bundle(root: Path) -> None:
    root.mkdir()
    (root / "index.md").write_text("---\ntitle: Index\n---\n[Table](tables/table.md)\n", encoding="utf-8")
    (root / "tables").mkdir()
    (root / "tables" / "table.md").write_text(
        "---\ntitle: Table\nkind: entity\n---\n# Sales table\n", encoding="utf-8"
    )


def test_preflight_and_explicit_native_operations(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write_bundle(root)
    consumer = OkfNativeConsumer(root, _target())

    preflight = consumer.preflight(1.0)
    listing = consumer.dispatch(NativeRequest("okf.list_files", {}, 1.0))
    read = consumer.dispatch(NativeRequest("okf.read_file", {"path": "index.md"}, 1.0))
    followed = consumer.dispatch(
        NativeRequest("okf.follow_link", {"source_path": "index.md", "link": "tables/table.md"}, 1.0)
    )
    searched = consumer.dispatch(NativeRequest("okf.search_text", {"query": "sales"}, 1.0))

    assert [item.status for item in preflight] == ["ok", "ok"]
    assert listing.output["count"] == 2
    assert read.output["artifact_sha256"]
    assert followed.output["path"] == "tables/table.md"
    assert searched.output["matches"][0]["path"] == "tables/table.md"
    assert all(event.operation.startswith("okf.") for event in consumer.access_events())
    assert all("content" not in event.to_dict() for event in consumer.access_events())


def test_rejects_path_traversal_symlink_escape_and_gold_root(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write_bundle(root)
    outside = tmp_path / "outside.md"
    outside.write_text("---\ntitle: outside\n---\n", encoding="utf-8")
    (root / "escape.md").symlink_to(outside)
    consumer = OkfNativeConsumer(root, _target())

    with pytest.raises(NativeIsolationError):
        consumer.read_file("../outside.md")
    with pytest.raises(NativeIsolationError):
        consumer.read_file("escape.md")
    with pytest.raises(OkfBundleError, match="Symlinked"):
        consumer.validate_frontmatter()
    with pytest.raises(NativeIsolationError):
        OkfNativeConsumer(root, _target("benchmark/tpcds/results/gold/sf1"))


def test_follow_requires_declared_local_link_and_no_database_fallback(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write_bundle(root)
    consumer = OkfNativeConsumer(root, _target())

    with pytest.raises(OkfBundleError, match="declared"):
        consumer.follow_link("index.md", "tables/not-declared.md")
    with pytest.raises(Exception, match="Undeclared"):
        consumer.dispatch(NativeRequest("db.execute_readonly", {"sql": "select 1"}, 1.0))
    assert "db.execute_readonly" not in {tool["name"] for tool in consumer.public_tools()}
