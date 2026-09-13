# Native adapters

[English](README.md) | [简体中文](README.zh-CN.md)

This directory holds narrow, target-specific adapters. It is not a shared
semantic-query API: every module preserves the target's documented operation
names and payload shape, and does not replace an unavailable target with direct
SQL.

## MetricFlow

[`metricflow.py`](metricflow.py) wraps only the official `mf` CLI command
surface at the source revision pinned in
[`../config/targets.native.yaml`](../config/targets.native.yaml):

| Benchmark operation | Pinned native command |
| --- | --- |
| `metricflow.health_checks` | `mf health-checks` |
| `metricflow.validate_configs` | `mf validate-configs` |
| `metricflow.list_metrics` | `mf list metrics` |
| `metricflow.list_dimensions` | `mf list dimensions --metrics <comma-separated>` |
| `metricflow.list_dimension_values` | `mf list dimension-values --metrics <…> --dimension <…>` |
| `metricflow.list_entities` | `mf list entities --metrics <comma-separated>` |
| `metricflow.query` | `mf query --metrics <comma-separated> …` |

The implementation pin is commit
[`8750c1d`](https://github.com/dbt-labs/metricflow/tree/8750c1dfe79c9d92e37fc9b8542d544e29f8852e),
whose package version is `0.213.0.dev0`. The commands above are taken from its
official CLI implementation, not reconstructed from the engine source.

Before any request, the adapter requires a successful version probe, a source
model-layout check, `health-checks`, and `validate-configs`. It runs commands in
an externally provisioned compatible dbt runtime project, while separately
recording the repository's pinned standalone model root. This distinction is
intentional: the checked-in standalone authoring files alone are not evidence
that a live dbt/MetricFlow runtime is configured.

Each response includes the original argv, return code, stdout/stderr, duration,
and deterministic SHA-256 request/response identities. The adapter never opens
a database connection, generates SQL, calls `db.execute_readonly`, or exposes
Gold artifacts. A recognized missing MetricFlow metric/dimension/entity is
recorded as `unsupported`; all other non-zero CLI exits are `failed`.

The unit tests use a fake subprocess boundary and make no claim that MetricFlow
was installed or executed in CI.
