# Semantic models

[English](README.md) | [简体中文](README.zh-CN.md)

This directory contains the common semantic contract and each benchmark target's native representation. All targets must describe the same PostgreSQL SF1 schema and business intent; differences should reflect format capabilities, not different inputs.

## Current status

| Representation | Location | Status | Purpose |
| --- | --- | --- | --- |
| Skill | [`skill/tpcds-sf1-table-semantics/`](skill/tpcds-sf1-table-semantics/) | Table semantics implemented | Agent instructions plus progressively loaded table references |
| OKF v0.2 | [`okf/tpcds-sf1/`](okf/tpcds-sf1/) | Table semantics implemented | Portable Markdown knowledge bundle with YAML metadata |
| Canonical | [`canonical/`](canonical/) | Planned | System-neutral semantic and metric contract |
| MetricFlow | [`metricflow/`](metricflow/) | Planned | MetricFlow-native semantic model |
| Cube | [`cube/`](cube/) | Planned | Cube-native data model |
| Ossie | [`ossie/`](ossie/) | Planned | Ossie-native semantic representation |
| DDL-only | [`ddl-only/`](ddl-only/) | Planned | Control baseline without enriched semantics |

Skill and OKF currently cover the same 24 business tables, 425 physical columns, and 106 explicit relationships. `dbgen_version` is excluded because it records generator metadata rather than retail business data.

## Shared table contract

Every implemented table definition includes:

- physical table name, business description, domain, kind, grain, and primary key;
- every PostgreSQL column's type, semantic role, meaning, and nullability;
- role-specific joins and cardinality, including sold, shipped, and returned dates;
- distinct billing, shipping, refunded, and returning customer roles;
- composite sale-to-return joins for store, catalog, and web line items;
- additive, non-additive, and semi-additive measure guidance.

The two representations encode this contract differently. Skill packages behavioral instructions and keeps detailed tables under `references/` for progressive loading. OKF uses a v0.2 bundle whose table concepts carry YAML frontmatter and Markdown bodies. OKF is evaluated here as a knowledge representation, not assumed to be an executable SQL semantic engine.

## Source chain

The definitions are derived from these pinned sources:

1. **Logical model and benchmark terminology:** [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf).
2. **Physical PostgreSQL tables, columns, types, nullability, and primary keys:** [pinned PostgreSQL DDL at commit `63ee712`](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql).
3. **OKF packaging rules:** [Open Knowledge Format v0.2 specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md).

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

This version defines **table semantics only**. It does not yet define the canonical metric inventory, metric formulas, question-to-metric mappings, system-specific metric syntax, or executable adapters. Those artifacts should be added after the 99 questions are analyzed into a shared metric contract.

