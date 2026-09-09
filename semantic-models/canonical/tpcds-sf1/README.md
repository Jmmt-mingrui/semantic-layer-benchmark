# Canonical TPC-DS SF1 business metrics

[English](README.md) | [简体中文](README.zh-CN.md)

This directory contains the first system-neutral business-metric contract extracted from the 99 canonical questions and their 103 PostgreSQL reference SQL files.

## Artifacts

| File | Purpose |
| --- | --- |
| [`metrics.yaml`](metrics.yaml) | Reusable base metric families, derived metrics, and benchmark-specific formulas |
| [`question-metric-map.yaml`](question-metric-map.yaml) | Complete q01-q99 mapping from each question to metrics and analysis operations |

The candidate contract currently contains 42 base metric families, 25 reusable derived metrics, 9 query-exact metric definitions, and mappings for all 99 questions.

## Extraction method

Each question is interpreted in this order:

1. The official TPC-DS toolkit template defines intended query behavior.
2. The local attributed PostgreSQL SQL defines the executable formula used by this benchmark.
3. The canonical natural-language question supplies business wording and symbolic parameters.

A reusable numeric aggregation or ratio becomes a metric candidate. Grouping fields, filters, joins, rankings, set intersections, thresholds, and rollups are stored as `analysis_operations`; they are not automatically promoted to business metrics.

Channel variants share a metric family only when they express the same business concept. For example, store, catalog, and web extended sales prices are variants of `sales_revenue`. Expressions such as `SUM(ss_sales_price)` remain under `sales_price_sum` because summing a unit-price column is not equivalent to summing extended sales revenue.

## Metric layers

- **Base metric families** bind reusable business meanings to exact store, catalog, web, return, or inventory expressions.
- **Derived metrics** define reusable cross-channel totals, shares, growth, margins, return ratios, averages, variation, cumulative values, and conditional counts.
- **Query-exact metrics** preserve unusual formulas required for SQL equivalence. They are explicitly labeled so downstream systems do not present them as standard enterprise KPI definitions.

## Question and SQL alignment

The extraction found clear conflicts between several existing question paraphrases and their reference SQL:

- q51 describes a promotional-share question, while `query51.sql` compares cumulative web and store sales-price sums.
- q76 describes web promotional averages, while `query76.sql` reports counts and extended sales amounts for rows with selected null foreign keys.
- q97 describes a promotion ratio, while `query97.sql` counts store-only, catalog-only, and shared customer-item pairs.

`question-metric-map.yaml` records SQL-aligned `question_override` text for those conflicts. It also sharpens ambiguous wording for q48, q66, q78, q85, q91, and q98. The source `questions.jsonl` is intentionally unchanged in this first metric commit so question corrections can be reviewed separately.

## Benchmark use

This candidate layer is the shared target for MetricFlow, Cube, Ossie, Skill, and OKF representations. A native implementation should record whether each canonical metric is represented directly, decomposed into measures plus query logic, approximated, or unsupported.

Metric extraction does not imply that every TPC-DS query can be answered by selecting one named metric. Many questions require cohorts, correlated thresholds, full outer joins, intersections, rollups, or window functions; those structural requirements are retained in the question mapping.

## Current boundary

This is a reviewable v0.1 candidate inventory, not the final KPI contract. Before native-system translation, the next review should:

1. approve the SQL-aligned question corrections;
2. verify query-exact formulas against the official toolkit templates;
3. decide which query-exact expressions should remain local rather than become reusable metrics;
4. assign canonical dimensions, entities, time grains, and required join paths to every mapping.
