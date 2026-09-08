---
type: PostgreSQL Table
title: Promotion
description: Promotion identity, active dates, cost, target, channels, purpose, and discount state.
resource: urn:tpcds:sf1:postgresql:public:promotion
tags: [tpc-ds-derived, sf1, shared, dimension]
status: draft
generated: { by: process:semantic-layer-benchmark, at: 2026-09-08T13:54:53Z }
table: public.promotion
kind: dimension
domain: shared
grain: One row per promotion surrogate key.
primary_key: [p_promo_sk]
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

# Promotion

Promotion identity, active dates, cost, target, channels, purpose, and discount state.

## Semantic contract

- **Physical table:** `public.promotion`
- **Kind:** dimension
- **Domain:** shared
- **Grain:** One row per promotion surrogate key.
- **Primary key:** `p_promo_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `p_promo_sk` | `integer` | primary key | Surrogate key component identifying the promotion row. |
| `p_promo_id` | `char(16)` | business identifier | Business identifier for promotion. |
| `p_start_date_sk` | `integer` | foreign key | Surrogate key to Date; promotion start date. Nullable. |
| `p_end_date_sk` | `integer` | foreign key | Surrogate key to Date; promotion end date. Nullable. |
| `p_item_sk` | `integer` | foreign key | Surrogate key to Item; promoted item. Nullable. |
| `p_cost` | `decimal(15,2)` | attribute | Cost. Nullable. |
| `p_response_target` | `integer` | attribute | Response target. Nullable. |
| `p_promo_name` | `char(50)` | attribute | Promotion name. Nullable. |
| `p_channel_dmail` | `char(1)` | flag | Flag indicating channel direct mail. Nullable. |
| `p_channel_email` | `char(1)` | flag | Flag indicating channel email. Nullable. |
| `p_channel_catalog` | `char(1)` | flag | Flag indicating channel catalog. Nullable. |
| `p_channel_tv` | `char(1)` | flag | Flag indicating channel tv. Nullable. |
| `p_channel_radio` | `char(1)` | flag | Flag indicating channel radio. Nullable. |
| `p_channel_press` | `char(1)` | flag | Flag indicating channel press. Nullable. |
| `p_channel_event` | `char(1)` | flag | Flag indicating channel event. Nullable. |
| `p_channel_demo` | `char(1)` | flag | Flag indicating channel demo. Nullable. |
| `p_channel_details` | `varchar(100)` | flag | Flag indicating channel details. Nullable. |
| `p_purpose` | `char(15)` | attribute | Purpose. Nullable. |
| `p_discount_active` | `char(1)` | flag | Flag indicating discount active. Nullable. |

## Relationships

| Local columns | Target | Cardinality | Meaning |
| --- | --- | --- | --- |
| `p_start_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Promotion start date. |
| `p_end_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Promotion end date. |
| `p_item_sk` | [item](item.md).`i_item_sk` | many-to-one | Promoted item. |

## Query guidance

- Channel flags describe where a promotion was advertised, not where the resulting sale occurred.
- A null promotion key on a fact represents an unpromoted sale.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
