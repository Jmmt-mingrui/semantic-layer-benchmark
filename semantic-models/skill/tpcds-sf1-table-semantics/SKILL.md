---
name: tpcds-sf1-table-semantics
description: Interpret TPC-DS SF1 PostgreSQL tables and canonical business metrics, then generate read-only analytical SQL using documented grain, joins, metric formulas, variants, and analysis operations. Use only for the TPC-DS-derived benchmark schema.
---

# TPC-DS SF1 table semantics

Use this skill to translate benchmark questions into schema-aware SQL or to explain the TPC-DS-derived PostgreSQL model.

Read [the schema overview](references/schema-overview.md) first. For aggregate, ratio, comparison, ranking, or KPI questions, also read [the business metric index](references/metrics/index.md). Then load only the table and metric references required by the question.

## Required behavior

- Preserve each fact table's declared grain before aggregating or joining.
- Join facts to dimensions through surrogate keys and keep role-playing date, customer, demographic, and address keys distinct.
- Join a return line to its originating sale with the complete composite key documented for that channel.
- Treat sales and return line totals as additive unless a column is explicitly marked non-additive.
- Treat inventory quantity as semi-additive and never sum snapshots across dates without an explicit inventory-flow interpretation.
- Use sold date for demand analysis, ship date for fulfillment analysis, and returned date for return analysis.
- Generate read-only PostgreSQL SQL and qualify ambiguous columns.
- Resolve the benchmark question in the question-to-metric map before choosing formulas.
- Preserve canonical metric IDs, channel variants, value types, and additivity rules.
- Compute derived metrics only after their inputs have compatible grouping grain and filters.
- Treat `analysis_operations` as query logic rather than inventing metrics for ranks, buckets, filters, or intersections.
- Use query-exact metrics verbatim when mapped; do not silently replace unusual TPC-DS formulas with conventional KPIs.
- When a question paraphrase conflicts with reference SQL, follow the recorded SQL-aligned override and report the conflict.

The table files are semantic documentation, not a claim of an audited TPC benchmark implementation. For source and licensing boundaries, follow the links in each table reference.
