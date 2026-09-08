---
type: PostgreSQL Table
title: Income Band
description: Lower and upper household-income bounds used by household demographics.
resource: urn:tpcds:sf1:postgresql:public:income_band
tags: [tpc-ds-derived, sf1, shared, dimension]
status: draft
generated: { by: process:semantic-layer-benchmark, at: 2026-09-08T13:54:53Z }
table: public.income_band
kind: dimension
domain: shared
grain: One row per income-band range.
primary_key: [ib_income_band_sk]
sources:
  - id: tpcds-v4-spec
    resource: https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf
    title: TPC-DS v4.0.0 specification
    author: organization:tpc
  - id: benchmark-postgres-ddl
    resource: https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql
    title: Pinned PostgreSQL DDL used by the benchmark
    author: process:litkhai-tpcds-scripts
---

# Income Band

Lower and upper household-income bounds used by household demographics.

## Semantic contract

- **Physical table:** `public.income_band`
- **Kind:** dimension
- **Domain:** shared
- **Grain:** One row per income-band range.
- **Primary key:** `ib_income_band_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `ib_income_band_sk` | `integer` | primary key | Surrogate key component identifying the income band row. |
| `ib_lower_bound` | `integer` | attribute | Lower bound. Nullable. |
| `ib_upper_bound` | `integer` | attribute | Upper bound. Nullable. |

## Relationships

No outbound semantic joins are defined for this table.

## Query guidance

- Join through household_demographics rather than directly from sales facts.
- Treat the bounds as an interval, not as additive measures.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
