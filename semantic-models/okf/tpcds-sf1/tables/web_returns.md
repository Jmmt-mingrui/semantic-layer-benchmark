---
type: PostgreSQL Table
title: Web Returns
description: Returned web line items, refunded and returning customer roles, reason, and financial effects.
resource: urn:tpcds:sf1:postgresql:public:web_returns
tags: [tpc-ds-derived, sf1, web, fact]
status: draft
generated: { by: process:semantic-layer-benchmark, at: 2026-09-08T13:54:53Z }
table: public.web_returns
kind: fact
domain: web
grain: One returned web line item per item and order number.
primary_key: [wr_item_sk, wr_order_number]
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

# Web Returns

Returned web line items, refunded and returning customer roles, reason, and financial effects.

## Semantic contract

- **Physical table:** `public.web_returns`
- **Kind:** fact
- **Domain:** web
- **Grain:** One returned web line item per item and order number.
- **Primary key:** `wr_item_sk`, `wr_order_number`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `wr_returned_date_sk` | `integer` | foreign key | Surrogate key to Date; return date. Nullable. |
| `wr_returned_time_sk` | `integer` | foreign key | Surrogate key to Time; return time. Nullable. |
| `wr_item_sk` | `integer` | primary key | Surrogate key to Web Sales; matching web sale line. |
| `wr_refunded_customer_sk` | `integer` | foreign key | Surrogate key to Customer; refunded customer. Nullable. |
| `wr_refunded_cdemo_sk` | `integer` | foreign key | Surrogate key to Customer Demographics; refunded customer demographics. Nullable. |
| `wr_refunded_hdemo_sk` | `integer` | foreign key | Surrogate key to Household Demographics; refunded household demographics. Nullable. |
| `wr_refunded_addr_sk` | `integer` | foreign key | Surrogate key to Customer Address; refund address. Nullable. |
| `wr_returning_customer_sk` | `integer` | foreign key | Surrogate key to Customer; returning customer. Nullable. |
| `wr_returning_cdemo_sk` | `integer` | foreign key | Surrogate key to Customer Demographics; returning customer demographics. Nullable. |
| `wr_returning_hdemo_sk` | `integer` | foreign key | Surrogate key to Household Demographics; returning household demographics. Nullable. |
| `wr_returning_addr_sk` | `integer` | foreign key | Surrogate key to Customer Address; returning customer address. Nullable. |
| `wr_web_page_sk` | `integer` | foreign key | Surrogate key to Web Page; web page. Nullable. |
| `wr_reason_sk` | `integer` | foreign key | Surrogate key to Return Reason; return reason. Nullable. |
| `wr_order_number` | `integer` | primary key | Surrogate key to Web Sales; matching web sale line. |
| `wr_return_quantity` | `integer` | additive measure | Number of units returned on the line. Nullable. |
| `wr_return_amt` | `decimal(7,2)` | additive measure | Returned merchandise amount. Nullable. |
| `wr_return_tax` | `decimal(7,2)` | additive measure | Tax amount associated with the return. Nullable. |
| `wr_return_amt_inc_tax` | `decimal(7,2)` | additive measure | Return amount including tax. Nullable. |
| `wr_fee` | `decimal(7,2)` | additive measure | Return fee charged for the line. Nullable. |
| `wr_return_ship_cost` | `decimal(7,2)` | additive measure | Shipping cost associated with the return. Nullable. |
| `wr_refunded_cash` | `decimal(7,2)` | attribute | Return value refunded as cash. Nullable. |
| `wr_reversed_charge` | `decimal(7,2)` | additive measure | Return value credited by reversing a charge. Nullable. |
| `wr_account_credit` | `decimal(7,2)` | additive measure | Return value issued as account credit. Nullable. |
| `wr_net_loss` | `decimal(7,2)` | additive measure | Net loss attributed to the returned line. Nullable. |

## Relationships

| Local columns | Target | Cardinality | Meaning |
| --- | --- | --- | --- |
| `wr_returned_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Return date. |
| `wr_returned_time_sk` | [time_dim](time_dim.md).`t_time_sk` | many-to-one | Return time. |
| `wr_item_sk` | [item](item.md).`i_item_sk` | many-to-one | Returned item. |
| `wr_refunded_customer_sk` | [customer](customer.md).`c_customer_sk` | many-to-one | Refunded customer. |
| `wr_refunded_cdemo_sk` | [customer_demographics](customer_demographics.md).`cd_demo_sk` | many-to-one | Refunded customer demographics. |
| `wr_refunded_hdemo_sk` | [household_demographics](household_demographics.md).`hd_demo_sk` | many-to-one | Refunded household demographics. |
| `wr_refunded_addr_sk` | [customer_address](customer_address.md).`ca_address_sk` | many-to-one | Refund address. |
| `wr_returning_customer_sk` | [customer](customer.md).`c_customer_sk` | many-to-one | Returning customer. |
| `wr_returning_cdemo_sk` | [customer_demographics](customer_demographics.md).`cd_demo_sk` | many-to-one | Returning customer demographics. |
| `wr_returning_hdemo_sk` | [household_demographics](household_demographics.md).`hd_demo_sk` | many-to-one | Returning household demographics. |
| `wr_returning_addr_sk` | [customer_address](customer_address.md).`ca_address_sk` | many-to-one | Returning customer address. |
| `wr_web_page_sk` | [web_page](web_page.md).`wp_web_page_sk` | many-to-one | Web page. |
| `wr_reason_sk` | [reason](reason.md).`r_reason_sk` | many-to-one | Return reason. |
| `wr_item_sk`, `wr_order_number` | [web_sales](web_sales.md).`ws_item_sk`, `ws_order_number` | one-to-one (optional) | Matching web sale line. |

## Query guidance

- Join to web sales with both item key and order number.
- Returning-customer and refunded-customer roles are distinct.
- Return amounts and quantities are additive.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
