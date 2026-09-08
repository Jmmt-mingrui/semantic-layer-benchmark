---
type: PostgreSQL Table
title: Warehouse
description: Warehouse identity, capacity, address, geography, and time-zone attributes.
resource: urn:tpcds:sf1:postgresql:public:warehouse
tags: [tpc-ds-derived, sf1, shared, dimension]
status: draft
generated: { by: process:semantic-layer-benchmark, at: 2026-09-08T13:54:53Z }
table: public.warehouse
kind: dimension
domain: shared
grain: One row per warehouse surrogate key.
primary_key: [w_warehouse_sk]
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

# Warehouse

Warehouse identity, capacity, address, geography, and time-zone attributes.

## Semantic contract

- **Physical table:** `public.warehouse`
- **Kind:** dimension
- **Domain:** shared
- **Grain:** One row per warehouse surrogate key.
- **Primary key:** `w_warehouse_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `w_warehouse_sk` | `integer` | primary key | Surrogate key component identifying the warehouse row. |
| `w_warehouse_id` | `char(16)` | business identifier | Business identifier for warehouse. |
| `w_warehouse_name` | `varchar(20)` | attribute | Warehouse name. Nullable. |
| `w_warehouse_sq_ft` | `integer` | attribute | Warehouse square feet. Nullable. |
| `w_street_number` | `char(10)` | business identifier | Street number. Nullable. |
| `w_street_name` | `varchar(60)` | attribute | Street name. Nullable. |
| `w_street_type` | `char(15)` | attribute | Street type. Nullable. |
| `w_suite_number` | `char(10)` | business identifier | Suite number. Nullable. |
| `w_city` | `varchar(60)` | attribute | City. Nullable. |
| `w_county` | `varchar(30)` | attribute | County. Nullable. |
| `w_state` | `char(2)` | attribute | State. Nullable. |
| `w_zip` | `char(10)` | attribute | Zip. Nullable. |
| `w_country` | `varchar(20)` | attribute | Country. Nullable. |
| `w_gmt_offset` | `decimal(5,2)` | attribute | Offset from Greenwich Mean Time in hours. Nullable. |

## Relationships

No outbound semantic joins are defined for this table.

## Query guidance

- Warehouse joins describe inventory location or catalog/web fulfillment location.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
