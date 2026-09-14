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

## Apache Ossie native consumer

[`ossie.py`](ossie.py) reads the Ossie model as native YAML and does not
translate it into Skill, OKF, normalized chunks, or a shared `SemanticEvidence`
representation. The benchmark target is pinned to Apache Ossie commit
[`c109cf5`](https://github.com/apache/ossie/tree/c109cf5b0a06970a97599e8f7c2a72859822a3a4)
and to `core-spec/ossie-schema.json` at blob
`4e50f1eeafd3c56c700e6c5482f9b356b34e1fee`. A vendored copy used by CI lives
under [`schemas/ossie-c109cf5-schema.json`](schemas/ossie-c109cf5-schema.json).

The consumer implements three Ossie operations:

| Operation | Behavior |
| --- | --- |
| `ossie.validate` | Validate the original YAML with the pinned official JSON Schema and validate Dataset/Field/Relationship/Metric references. |
| `ossie.inspect_model` | Discover native objects by type and optional native ID without returning normalized semantic content. |
| `ossie.read_native_yaml` | Return the complete original YAML or the exact source slice for one Dataset, Field, Relationship, Metric, or semantic model. |

Object discovery indexes source locations only after successful validation. A
Field can be addressed by its fully qualified native ID such as
`tpcds_sf1_retail/store_sales/ss_item_sk`; short IDs are accepted only when
unambiguous. Returned YAML is taken directly from the original source text.

Access telemetry contains operation, object type/ID, byte count, duration, and
SHA-256 identity. It never records YAML content, SQL, query results, benchmark
Gold, or question-to-metric mappings. The consumer rejects traversal, symlinks,
evaluator/Gold roots, undeclared operations, shared semantic conversion,
embeddings, and vector indexes.

Ossie is not treated as a SQL runtime. `db.execute_readonly` remains a separate
harness operation: the Agent authors SQL and the benchmark executes it through
the read-only DuckDB boundary. The Ossie consumer itself never opens DuckDB or
implements a synthetic Ossie query engine.

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
