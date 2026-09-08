---
type: PostgreSQL Table
title: Catalog Page
description: Catalog page, department, catalog number, and active-date attributes.
resource: urn:tpcds:sf1:postgresql:public:catalog_page
tags: [tpc-ds-derived, sf1, catalog, dimension]
status: draft
generated: { by: process:semantic-layer-benchmark, at: 2026-09-08T13:54:53Z }
table: public.catalog_page
kind: dimension
domain: catalog
grain: One row per catalog page surrogate key.
primary_key: [cp_catalog_page_sk]
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

# Catalog Page

Catalog page, department, catalog number, and active-date attributes.

## Semantic contract

- **Physical table:** `public.catalog_page`
- **Kind:** dimension
- **Domain:** catalog
- **Grain:** One row per catalog page surrogate key.
- **Primary key:** `cp_catalog_page_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `cp_catalog_page_sk` | `integer` | primary key | Surrogate key component identifying the catalog page row. |
| `cp_catalog_page_id` | `char(16)` | business identifier | Business identifier for catalog page. |
| `cp_start_date_sk` | `integer` | foreign key | Surrogate key to Date; catalog-page start date. Nullable. |
| `cp_end_date_sk` | `integer` | foreign key | Surrogate key to Date; catalog-page end date. Nullable. |
| `cp_department` | `varchar(50)` | attribute | Department. Nullable. |
| `cp_catalog_number` | `integer` | business identifier | Catalog number. Nullable. |
| `cp_catalog_page_number` | `integer` | business identifier | Catalog page number. Nullable. |
| `cp_description` | `varchar(100)` | attribute | Description. Nullable. |
| `cp_type` | `varchar(100)` | attribute | Type. Nullable. |

## Relationships

| Local columns | Target | Cardinality | Meaning |
| --- | --- | --- | --- |
| `cp_start_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Catalog-page start date. |
| `cp_end_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Catalog-page end date. |

## Query guidance

- Use the catalog-page key carried by the fact row.
- Start and end date keys describe when the page is active.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
