---
type: PostgreSQL Table
title: Web Page
description: Versioned web-page identity, lifecycle, ownership, URL, type, and content-volume attributes.
resource: urn:tpcds:sf1:postgresql:public:web_page
tags: [tpc-ds-derived, sf1, web, dimension]
status: draft
generated: { by: process:semantic-layer-benchmark, at: 2026-09-08T13:54:53Z }
table: public.web_page
kind: dimension
domain: web
grain: One slowly changing dimension row per web-page version.
primary_key: [wp_web_page_sk]
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

# Web Page

Versioned web-page identity, lifecycle, ownership, URL, type, and content-volume attributes.

## Semantic contract

- **Physical table:** `public.web_page`
- **Kind:** dimension
- **Domain:** web
- **Grain:** One slowly changing dimension row per web-page version.
- **Primary key:** `wp_web_page_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `wp_web_page_sk` | `integer` | primary key | Surrogate key component identifying the web page row. |
| `wp_web_page_id` | `char(16)` | business identifier | Business identifier for web page. |
| `wp_rec_start_date` | `date` | date attribute | Date on which this dimension version became effective. Nullable. |
| `wp_rec_end_date` | `date` | date attribute | Date on which this dimension version stopped being effective. Nullable. |
| `wp_creation_date_sk` | `integer` | foreign key | Surrogate key to Date; page creation date. Nullable. |
| `wp_access_date_sk` | `integer` | foreign key | Surrogate key to Date; last page access date. Nullable. |
| `wp_autogen_flag` | `char(1)` | flag | Flag indicating auto-generated. Nullable. |
| `wp_customer_sk` | `integer` | foreign key | Surrogate key to Customer; associated customer. Nullable. |
| `wp_url` | `varchar(100)` | attribute | Url. Nullable. |
| `wp_type` | `char(50)` | attribute | Type. Nullable. |
| `wp_char_count` | `integer` | attribute | Char count. Nullable. |
| `wp_link_count` | `integer` | attribute | Link count. Nullable. |
| `wp_image_count` | `integer` | attribute | Image count. Nullable. |
| `wp_max_ad_count` | `integer` | attribute | Max ad count. Nullable. |

## Relationships

| Local columns | Target | Cardinality | Meaning |
| --- | --- | --- | --- |
| `wp_creation_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Page creation date. |
| `wp_access_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Last page access date. |
| `wp_customer_sk` | [customer](customer.md).`c_customer_sk` | many-to-one | Associated customer. |

## Query guidance

- Creation date and last-access date are separate roles.
- The optional customer key identifies an associated customer, not the visitor on each sale.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
