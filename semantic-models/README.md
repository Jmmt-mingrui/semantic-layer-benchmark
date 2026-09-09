# Semantic models

[English](README.md) | [简体中文](README.zh-CN.md)

This directory contains the common semantic contract and each benchmark target's native representation. All targets must describe the same PostgreSQL SF1 schema and business intent; differences should reflect format capabilities, not different inputs.

## Current status

| Representation | Location | Status | Purpose |
| --- | --- | --- | --- |
| Skill | [`skill/tpcds-sf1-table-semantics/`](skill/tpcds-sf1-table-semantics/) | Table and metric semantics implemented | Agent instructions plus progressively loaded table and metric references |
| OKF v0.2 | [`okf/tpcds-sf1/`](okf/tpcds-sf1/) | Table and metric semantics implemented | Portable Markdown knowledge bundle with YAML metadata |
| Canonical | [`canonical/tpcds-sf1/`](canonical/tpcds-sf1/) | Candidate metrics extracted | System-neutral metric catalog and q01-q99 mapping |
| MetricFlow | [`metricflow/tpcds-sf1/`](metricflow/tpcds-sf1/) | Table semantics implemented | Standalone MetricFlow YAML models and base metrics |
| Cube | [`cube/`](cube/) | Planned | Cube-native data model |
| Ossie | [`ossie/tpcds-sf1/`](ossie/tpcds-sf1/) | Table semantics implemented | Apache Ossie `0.2.0.dev0` YAML exchange document |
| DDL-only | [`ddl-only/`](ddl-only/) | Planned | Control baseline without enriched semantics |

Skill, OKF, MetricFlow, and Ossie currently describe the same 24 business tables and 425 physical columns. MetricFlow and Ossie additionally define 64 additive base aggregations; Ossie carries all 106 relationships as explicit objects, while MetricFlow encodes the same join paths through shared entities. The canonical SF1 layer now adds a candidate catalog of 42 base metric families, 25 derived metrics, 9 query-exact formulas, and mappings for all 99 questions. `dbgen_version` is excluded because it records generator metadata rather than retail business data.

## Shared table contract

Every implemented table definition includes:

- physical table name, business description, domain, kind, grain, and primary key;
- every PostgreSQL column's type, semantic role, meaning, and nullability;
- role-specific joins and cardinality, including sold, shipped, and returned dates;
- distinct billing, shipping, refunded, and returning customer roles;
- composite sale-to-return joins for store, catalog, and web line items;
- additive, non-additive, and semi-additive measure guidance.

The representations encode this contract differently. Skill packages behavioral instructions and keeps detailed tables under `references/` for progressive loading. OKF uses a v0.2 bundle whose table concepts carry YAML frontmatter and Markdown bodies. MetricFlow represents joins as shared entities and uses local PostgreSQL date expressions for fact aggregation time. Ossie expresses datasets, fields, relationships, and aggregate expressions in a vendor-neutral document. In the official Ossie shape, the top-level `semantic_model` is the complete-model container and its `datasets` array holds logical fact and dimension tables; the one-file layout used here is a canonical packaging choice, not a one-table limitation. See the [official Core Metadata Specification](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/core-spec/spec.md#semantic-model) and [official TPC-DS example](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/examples/tpcds_semantic_model.yaml). OKF is evaluated here as a knowledge representation, not assumed to be an executable SQL semantic engine.

## Source chain

The definitions are derived from these pinned sources:

1. **Logical model and benchmark terminology:** [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf).
2. **Physical PostgreSQL tables, columns, types, nullability, and primary keys:** [pinned PostgreSQL DDL at commit `63ee712`](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql).
3. **OKF packaging rules:** [Open Knowledge Format v0.2 specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md).
4. **MetricFlow authoring and validation:** [pinned MetricFlow source](https://github.com/dbt-labs/metricflow/tree/8750c1dfe79c9d92e37fc9b8542d544e29f8852e).
5. **Ossie authoring and validation:** [pinned Apache Ossie source](https://github.com/apache/ossie/tree/c109cf5b0a06970a97599e8f7c2a72859822a3a4).

This project is TPC-DS-derived and is not an audited TPC benchmark implementation. The repository does not vendor the TPC toolkit or generated SF1 data.

## Modeling rules

- Keep the physical table grain unchanged before aggregation.
- Join through surrogate keys; do not infer joins from similarly named descriptive fields.
- Keep every role-playing key distinct even when roles target the same dimension table.
- Aggregate facts before broad fact-to-fact comparisons to prevent fanout.
- Sum transaction-line quantities and extended amounts across rows when appropriate.
- Do not sum unit prices or unit costs; use a justified average or weighted calculation.
- Treat inventory quantity on hand as semi-additive and do not sum it across snapshot dates.

## Current boundary

This version defines table semantics, base additive inputs, a **candidate canonical business-metric inventory**, and its complete Skill and OKF representations. The metric names, query-exact formulas, question overrides, dimensions, grains, and join requirements still require review before executable adapters and the remaining native-system translations are added.
