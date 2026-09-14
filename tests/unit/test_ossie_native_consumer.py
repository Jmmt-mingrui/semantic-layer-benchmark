from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from runner.adapters.ossie import (
    OSSIE_SCHEMA_BLOB_SHA,
    OSSIE_SCHEMA_COMMIT,
    OSSIE_SCHEMA_FILE,
    OssieAdapter,
    OssieConfigurationError,
    OssieValidationError,
)
from runner.core.native_adapter import NativeIsolationError, NativeOperationError, NativeRequest


ROOT = Path(__file__).resolve().parents[2]
MODEL_ROOT = ROOT / "semantic-models/ossie/tpcds-sf1"


def _target(root: str = "semantic-models/ossie/tpcds-sf1") -> dict[str, object]:
    return {
        "role": "semantic_interchange_specification",
        "native_surface": {
            "name": "ossie_yaml_spec_consumer",
            "artifact_root": root,
            "model_file": "tpcds-sf1.yaml",
            "schema_commit": OSSIE_SCHEMA_COMMIT,
            "schema_path": "core-spec/ossie-schema.json",
            "schema_blob_sha": OSSIE_SCHEMA_BLOB_SHA,
        },
        "preflight_operations": ["ossie.validate"],
        "allowed_operations": [
            "ossie.inspect_model",
            "ossie.read_native_yaml",
            "db.execute_readonly",
            "benchmark.submit_result",
        ],
        "prohibited_operations": ["semantic.normalized_chunks", "benchmark.read_gold"],
    }


def _write_minimal_model(root: Path) -> None:
    root.mkdir(parents=True)
    (root / "tpcds-sf1.yaml").write_text(
        """version: 0.2.0.dev0
semantic_model:
- name: retail
  datasets:
  - name: sales
    source: main.sales
    primary_key: [sale_id]
    fields:
    - name: sale_id
      expression:
        dialects:
        - dialect: ANSI_SQL
          expression: sale_id
      datatype: Integer
    - name: amount
      expression:
        dialects:
        - dialect: ANSI_SQL
          expression: amount
      datatype: Decimal
  relationships: []
  metrics:
  - name: revenue
    expression:
      dialects:
      - dialect: ANSI_SQL
        expression: SUM(sales.amount)
    datatype: Decimal
""",
        encoding="utf-8",
    )


def test_pinned_official_schema_and_full_tpcds_inventory_are_valid() -> None:
    adapter = OssieAdapter(target_config=_target(), model_root=MODEL_ROOT)

    response = adapter.preflight(10)[0]
    inventory = adapter.dispatch(NativeRequest("ossie.inspect_model", {}, 5))

    assert response.status == "succeeded"
    assert response.output["schema_commit"] == OSSIE_SCHEMA_COMMIT
    assert response.output["schema_blob_sha"] == OSSIE_SCHEMA_BLOB_SHA
    assert response.output["schema_sha256"]
    assert response.output["counts"] == {
        "dataset": 24,
        "field": 425,
        "relationship": 106,
        "metric": 64,
    }
    assert inventory.output["counts"] == response.output["counts"]


def test_mutated_vendored_schema_fails_closed(tmp_path: Path) -> None:
    schema = tmp_path / "ossie-schema.json"
    original = OSSIE_SCHEMA_FILE.read_bytes()
    schema.write_bytes(original + b"\n")

    adapter = OssieAdapter(target_config=_target(), model_root=MODEL_ROOT, schema_path=schema)

    with pytest.raises(OssieValidationError, match="do not match the pinned upstream Git blob"):
        adapter.preflight(10)


def test_inspect_filters_by_native_object_type_and_id() -> None:
    adapter = OssieAdapter(target_config=_target(), model_root=MODEL_ROOT)
    adapter.preflight(10)

    datasets = adapter.dispatch(NativeRequest("ossie.inspect_model", {"object_type": "dataset"}, 5))
    store_sales = adapter.dispatch(
        NativeRequest("ossie.inspect_model", {"object_type": "dataset", "object_id": "store_sales"}, 5)
    )
    fields = adapter.dispatch(NativeRequest("ossie.inspect_model", {"object_type": "field"}, 5))

    assert datasets.output["count"] == 24
    assert store_sales.output["object"]["id"] == "store_sales"
    assert store_sales.output["object"]["qualified_id"] == "tpcds_sf1_retail/store_sales"
    assert fields.output["count"] == 425
    assert any(item["qualified_id"].endswith("/store_sales/ss_item_sk") for item in fields.output["objects"])


def test_read_returns_exact_slice_from_original_yaml() -> None:
    adapter = OssieAdapter(target_config=_target(), model_root=MODEL_ROOT)
    adapter.preflight(10)
    original = (MODEL_ROOT / "tpcds-sf1.yaml").read_text(encoding="utf-8")

    whole = adapter.dispatch(NativeRequest("ossie.read_native_yaml", {"path": "tpcds-sf1.yaml"}, 5))
    field = adapter.dispatch(
        NativeRequest(
            "ossie.read_native_yaml",
            {"object_type": "field", "object_id": "tpcds_sf1_retail/store_sales/ss_item_sk"},
            5,
        )
    )

    assert whole.output["content"] == original
    assert field.output["content"] in original
    parsed = yaml.safe_load(field.output["content"])
    assert isinstance(parsed, list)
    assert parsed[0]["name"] == "ss_item_sk"
    assert field.output["byte_count"] == len(field.output["content"].encode("utf-8"))
    assert field.output["artifact_sha256"]

    events = adapter.access_events()
    assert any(event.object_type == "field" and event.object_id == "ss_item_sk" for event in events)
    assert all("content" not in event.to_dict() for event in events)


def test_reference_validation_rejects_missing_dataset_fields(tmp_path: Path) -> None:
    root = tmp_path / "ossie"
    _write_minimal_model(root)
    text = (root / "tpcds-sf1.yaml").read_text(encoding="utf-8")
    (root / "tpcds-sf1.yaml").write_text(text.replace("sales.amount", "sales.missing_amount"), encoding="utf-8")

    adapter = OssieAdapter(target_config=_target(), model_root=root)

    with pytest.raises(OssieValidationError, match="unknown field"):
        adapter.preflight(5)


def test_rejects_traversal_gold_root_and_undeclared_operations(tmp_path: Path) -> None:
    root = tmp_path / "ossie"
    _write_minimal_model(root)
    adapter = OssieAdapter(target_config=_target(), model_root=root)
    adapter.preflight(5)

    with pytest.raises(NativeIsolationError):
        adapter.dispatch(NativeRequest("ossie.read_native_yaml", {"path": "../gold/result.json"}, 5))
    with pytest.raises(NativeOperationError):
        adapter.dispatch(NativeRequest("ossie.search", {}, 5))
    with pytest.raises(NativeIsolationError):
        adapter.dispatch(NativeRequest("benchmark.read_gold", {}, 5))
    with pytest.raises(OssieConfigurationError, match="does not own"):
        adapter.dispatch(NativeRequest("db.execute_readonly", {"sql": "select 1"}, 5))
    with pytest.raises(NativeIsolationError):
        OssieAdapter(target_config=_target("benchmark/tpcds/results/gold/sf1"), model_root=root)


def test_public_surface_has_no_sql_runtime_or_shared_evidence(tmp_path: Path) -> None:
    root = tmp_path / "ossie"
    _write_minimal_model(root)
    adapter = OssieAdapter(target_config=_target(), model_root=root)

    assert [tool["name"] for tool in adapter.public_tools()] == [
        "ossie.inspect_model",
        "ossie.read_native_yaml",
    ]
    rendered = repr(adapter.public_tools())
    assert "db.execute_readonly" not in rendered
    assert "semantic.normalized_chunks" not in rendered
    assert "embedding" not in rendered.lower()
