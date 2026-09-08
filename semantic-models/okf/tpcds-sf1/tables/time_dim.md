---
type: PostgreSQL Table
title: Time
description: Time-of-day attributes including hour, minute, second, AM/PM, shift, and meal period.
resource: urn:tpcds:sf1:postgresql:public:time_dim
tags: [tpc-ds-derived, sf1, shared, dimension]
status: draft
generated: { by: process:semantic-layer-benchmark, at: 2026-09-08T13:54:53Z }
table: public.time_dim
kind: dimension
domain: shared
grain: One row per time-of-day surrogate key.
primary_key: [t_time_sk]
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

# Time

Time-of-day attributes including hour, minute, second, AM/PM, shift, and meal period.

## Semantic contract

- **Physical table:** `public.time_dim`
- **Kind:** dimension
- **Domain:** shared
- **Grain:** One row per time-of-day surrogate key.
- **Primary key:** `t_time_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `t_time_sk` | `integer` | primary key | Surrogate key component identifying the time row. |
| `t_time_id` | `char(16)` | business identifier | Business identifier for time. |
| `t_time` | `integer` | attribute | Time. Nullable. |
| `t_hour` | `integer` | attribute | Hour. Nullable. |
| `t_minute` | `integer` | attribute | Minute. Nullable. |
| `t_second` | `integer` | attribute | Second. Nullable. |
| `t_am_pm` | `char(2)` | attribute | Am pm. Nullable. |
| `t_shift` | `char(20)` | attribute | Shift. Nullable. |
| `t_sub_shift` | `char(20)` | attribute | Sub shift. Nullable. |
| `t_meal_time` | `char(20)` | attribute | Meal time. Nullable. |

## Relationships

No outbound semantic joins are defined for this table.

## Query guidance

- Join the sold or returned time role independently from the date role.
- Use hour and minute for half-hour and meal-period filters.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
