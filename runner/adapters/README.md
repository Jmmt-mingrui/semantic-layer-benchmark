# Native target adapters

[English](README.md) | [简体中文](README.zh-CN.md)

This directory contains target-specific benchmark adapters. It is not a shared
semantic API: each adapter exposes only the target's declared native operations,
preserves native request shapes, and must fail closed instead of using a direct
SQL or cross-target fallback.

## MetricFlow adapter

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
whose package version is `0.213.0.dev0`. Before dispatch, the adapter requires
a successful version probe, source-model layout check, `health-checks`, and
`validate-configs` against an externally provisioned compatible dbt runtime
project. The repository's standalone model root is recorded separately and is
not treated as evidence of a live runtime.

Each response records native argv, return code, stdout/stderr, duration, and
deterministic request/response identities. The adapter never opens a database,
generates SQL, invokes `db.execute_readonly`, or exposes Gold artifacts.
Recognized missing semantic members are reported as `unsupported`; other
non-zero exits are `failed`. Unit tests use a fake subprocess boundary and do
not claim that MetricFlow runs in CI.

## Skill host adapter

`SkillHostAdapter` hosts
`semantic-models/skill/tpcds-sf1-table-semantics` as a native Skill package.
At discovery, it exposes only frontmatter-derived metadata and immutable package
and host revision identities. It does not enumerate or load `SKILL.md` or any
reference.

The agent must explicitly invoke `skill.activate`; only then does the host load
the complete `SKILL.md`. After activation, `skill.read_reference` reads exactly
one requested UTF-8 package-relative file. The host rejects traversal, absolute
paths, package symlinks, evaluator/Gold paths, preload-all operations, shared
chunk conversion, and undeclared fallbacks. Its access telemetry contains only
operation, sanitized relative path, byte count, SHA-256, and duration -- never
document content, SQL, results, or Gold data.

No score is produced by the Skill adapter. SQL execution and evaluation remain
separate, explicitly declared benchmark operations.
