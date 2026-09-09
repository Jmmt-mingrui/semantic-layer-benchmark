# MetricFlow TPC-DS SF1 semantics

[English](README.md) | [简体中文](README.zh-CN.md)

This directory uses MetricFlow's standalone YAML authoring form: one `semantic_model` document per physical PostgreSQL table, with direct `node_relation` mappings.

## Version pin

- MetricFlow source commit: [`8750c1d`](https://github.com/dbt-labs/metricflow/tree/8750c1dfe79c9d92e37fc9b8542d544e29f8852e)
- Parser/schema definition: [`metricflow_semantic_interfaces/parsing/schemas.py`](https://github.com/dbt-labs/metricflow/blob/8750c1dfe79c9d92e37fc9b8542d544e29f8852e/metricflow_semantic_interfaces/parsing/schemas.py)
- Physical schema: [pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql)
- Logical semantics: [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf)

This is the standalone specification used by the open-source MetricFlow parser, not dbt Core 1.12's newer model-embedded YAML form. The pin is intentional because the two formats are not interchangeable.

## Modeling decisions

- All 24 business tables map directly to `tpcds.public.<table>`.
- Primary, foreign, and unique entities encode simple and composite relationships.
- Role-playing joins use role-specific entity names backed by the same target key.
- Physical date keys are retained as entities. Because TPC-DS date surrogate keys are derived from Julian dates, PostgreSQL `to_date(..., 'J')` expressions provide local time dimensions for facts.
- Additive transaction fields are measures with `agg: sum`.
- Inventory quantity uses `non_additive_dimension` with the latest snapshot date.
- Unit prices and unit costs remain categorical dimensions; a later metric contract must define justified averages or weighted calculations.
- `create_metric: false` is explicit on every measure. Explicit simple metrics use a `total_` prefix, so no metric shares a measure name and duplicate proxy-metric definitions are avoided.

## Current boundary

These files define table semantics and reusable measure inputs. They do not yet define the canonical business metrics derived from the 99 benchmark questions.
