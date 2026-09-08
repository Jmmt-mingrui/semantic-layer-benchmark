---
type: PostgreSQL Table
title: Web Site
description: Versioned website operations, market, organization, address, time-zone, and tax attributes.
resource: urn:tpcds:sf1:postgresql:public:web_site
tags: [tpc-ds-derived, sf1, web, dimension]
status: draft
generated: { by: process:semantic-layer-benchmark, at: 2026-09-08T13:54:53Z }
table: public.web_site
kind: dimension
domain: web
grain: One slowly changing dimension row per website version.
primary_key: [web_site_sk]
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

# Web Site

Versioned website operations, market, organization, address, time-zone, and tax attributes.

## Semantic contract

- **Physical table:** `public.web_site`
- **Kind:** dimension
- **Domain:** web
- **Grain:** One slowly changing dimension row per website version.
- **Primary key:** `web_site_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `web_site_sk` | `integer` | primary key | Surrogate key component identifying the web site row. |
| `web_site_id` | `char(16)` | business identifier | Business identifier for site. |
| `web_rec_start_date` | `date` | date attribute | Date on which this dimension version became effective. Nullable. |
| `web_rec_end_date` | `date` | date attribute | Date on which this dimension version stopped being effective. Nullable. |
| `web_name` | `varchar(50)` | attribute | Name. Nullable. |
| `web_open_date_sk` | `integer` | foreign key | Surrogate key to Date; website opening date. Nullable. |
| `web_close_date_sk` | `integer` | foreign key | Surrogate key to Date; website closing date. Nullable. |
| `web_class` | `varchar(50)` | attribute | Class. Nullable. |
| `web_manager` | `varchar(40)` | attribute | Manager. Nullable. |
| `web_mkt_id` | `integer` | business identifier | Business identifier for market. Nullable. |
| `web_mkt_class` | `varchar(50)` | attribute | Market class. Nullable. |
| `web_mkt_desc` | `varchar(100)` | attribute | Market description. Nullable. |
| `web_market_manager` | `varchar(40)` | attribute | Market manager. Nullable. |
| `web_company_id` | `integer` | business identifier | Business identifier for company. Nullable. |
| `web_company_name` | `char(50)` | attribute | Company name. Nullable. |
| `web_street_number` | `char(10)` | business identifier | Street number. Nullable. |
| `web_street_name` | `varchar(60)` | attribute | Street name. Nullable. |
| `web_street_type` | `char(15)` | attribute | Street type. Nullable. |
| `web_suite_number` | `char(10)` | business identifier | Suite number. Nullable. |
| `web_city` | `varchar(60)` | attribute | City. Nullable. |
| `web_county` | `varchar(30)` | attribute | County. Nullable. |
| `web_state` | `char(2)` | attribute | State. Nullable. |
| `web_zip` | `char(10)` | attribute | Zip. Nullable. |
| `web_country` | `varchar(20)` | attribute | Country. Nullable. |
| `web_gmt_offset` | `decimal(5,2)` | attribute | Offset from Greenwich Mean Time in hours. Nullable. |
| `web_tax_percentage` | `decimal(5,2)` | attribute | Tax percentage. Nullable. |

## Relationships

| Local columns | Target | Cardinality | Meaning |
| --- | --- | --- | --- |
| `web_open_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Website opening date. |
| `web_close_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Website closing date. |

## Query guidance

- Join with web_site_sk from web sales.
- Open, close, and record-effective dates have different meanings.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
