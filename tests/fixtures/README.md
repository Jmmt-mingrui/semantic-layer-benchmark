# Synthetic TPC-DS-shaped protocol fixture

[English](README.md) | [简体中文](README.zh-CN.md)

This directory contains test-only support for exercising database, adapter, and artifact protocols in CI when the official generated dataset is unavailable.

`create_synthetic_tpcds_fixture()` creates the repository's 25 physical DuckDB tables and inserts exactly one deterministic synthetic row into each table. Integer surrogate keys use the same sentinel value so lightweight join-path tests can execute. The logical identity is stable for a fixed schema and fixture revision; DuckDB file bytes are not treated as a portable identity.

## Hard boundary

This fixture is **not TPC-DS data, not SF1, not a scaled dataset, and not a correctness oracle**. Its sidecar identity always declares:

- `publishable: false`;
- `ranking_eligible: false`;
- `tpcds_equivalence: none`;
- `scale_factor: null`;
- `gold_results: forbidden`.

The generator refuses to write beneath `data/tpcds/sf1/`, `benchmark/tpcds/results/gold/`, `runs/`, or `reports/generated/`. It never emits a dataset manifest or Gold result. Results obtained from it must be limited to protocol and CI assertions and must never be merged into benchmark scores, comparisons, charts, or claims.

## Test use

Create the database under the test framework's temporary directory:

```python
def test_adapter_protocol(tmp_path):
    database = tmp_path / "protocol.duckdb"
    identity = create_synthetic_tpcds_fixture(database, repository_root=REPOSITORY_ROOT)
    assert identity["ranking_eligible"] is False
```

Use the official `dsdgen` v4.0.0 flow documented in [`data/tpcds/sf1/README.md`](../../data/tpcds/sf1/README.md) for any publishable execution-correctness experiment.
