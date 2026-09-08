---
type: PostgreSQL Table
title: Item
description: Versioned product identity, hierarchy, manufacturer, price, physical, and manager attributes.
resource: urn:tpcds:sf1:postgresql:public:item
tags: [tpc-ds-derived, sf1, shared, dimension]
status: draft
generated: { by: process:semantic-layer-benchmark, at: 2026-09-08T13:54:53Z }
table: public.item
kind: dimension
domain: shared
grain: One slowly changing dimension row per item version.
primary_key: [i_item_sk]
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

# Item

Versioned product identity, hierarchy, manufacturer, price, physical, and manager attributes.

## Semantic contract

- **Physical table:** `public.item`
- **Kind:** dimension
- **Domain:** shared
- **Grain:** One slowly changing dimension row per item version.
- **Primary key:** `i_item_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `i_item_sk` | `integer` | primary key | Surrogate key component identifying the item row. |
| `i_item_id` | `char(16)` | business identifier | Business identifier for item. |
| `i_rec_start_date` | `date` | date attribute | Date on which this dimension version became effective. Nullable. |
| `i_rec_end_date` | `date` | date attribute | Date on which this dimension version stopped being effective. Nullable. |
| `i_item_desc` | `varchar(200)` | attribute | Item description. Nullable. |
| `i_current_price` | `decimal(7,2)` | flag | Flag indicating current price. Nullable. |
| `i_wholesale_cost` | `decimal(7,2)` | attribute | Wholesale cost per unit at the transaction. Nullable. |
| `i_brand_id` | `integer` | business identifier | Business identifier for brand. Nullable. |
| `i_brand` | `char(50)` | attribute | Brand. Nullable. |
| `i_class_id` | `integer` | business identifier | Business identifier for class. Nullable. |
| `i_class` | `char(50)` | attribute | Class. Nullable. |
| `i_category_id` | `integer` | business identifier | Business identifier for category. Nullable. |
| `i_category` | `char(50)` | attribute | Category. Nullable. |
| `i_manufact_id` | `integer` | business identifier | Business identifier for manufacturer. Nullable. |
| `i_manufact` | `char(50)` | attribute | Manufacturer. Nullable. |
| `i_size` | `char(20)` | attribute | Size. Nullable. |
| `i_formulation` | `char(20)` | attribute | Formulation. Nullable. |
| `i_color` | `char(20)` | attribute | Color. Nullable. |
| `i_units` | `char(10)` | attribute | Units. Nullable. |
| `i_container` | `char(10)` | attribute | Container. Nullable. |
| `i_manager_id` | `integer` | business identifier | Business identifier for manager. Nullable. |
| `i_product_name` | `char(50)` | attribute | Product name. Nullable. |

## Relationships

No outbound semantic joins are defined for this table.

## Query guidance

- Join facts with i_item_sk to preserve historical attributes.
- i_item_id is the stable business identity and may span multiple surrogate-key versions.
- Current price and wholesale cost are attributes, not additive facts.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
