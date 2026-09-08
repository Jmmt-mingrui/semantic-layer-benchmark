---
type: PostgreSQL Table
title: Catalog Returns
description: Returned catalog line items, refund roles, return reasons, and financial effects.
resource: urn:tpcds:sf1:postgresql:public:catalog_returns
tags: [tpc-ds-derived, sf1, catalog, fact]
status: draft
generated: { by: process:semantic-layer-benchmark, at: 2026-09-08T13:54:53Z }
table: public.catalog_returns
kind: fact
domain: catalog
grain: One returned catalog line item per item and order number.
primary_key: [cr_item_sk, cr_order_number]
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

# Catalog Returns

Returned catalog line items, refund roles, return reasons, and financial effects.

## Semantic contract

- **Physical table:** `public.catalog_returns`
- **Kind:** fact
- **Domain:** catalog
- **Grain:** One returned catalog line item per item and order number.
- **Primary key:** `cr_item_sk`, `cr_order_number`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `cr_returned_date_sk` | `integer` | foreign key | Surrogate key to Date; return date. Nullable. |
| `cr_returned_time_sk` | `integer` | foreign key | Surrogate key to Time; return time. Nullable. |
| `cr_item_sk` | `integer` | primary key | Surrogate key to Catalog Sales; matching catalog sale line. |
| `cr_refunded_customer_sk` | `integer` | foreign key | Surrogate key to Customer; refunded customer. Nullable. |
| `cr_refunded_cdemo_sk` | `integer` | foreign key | Surrogate key to Customer Demographics; refunded customer demographics. Nullable. |
| `cr_refunded_hdemo_sk` | `integer` | foreign key | Surrogate key to Household Demographics; refunded household demographics. Nullable. |
| `cr_refunded_addr_sk` | `integer` | foreign key | Surrogate key to Customer Address; refund address. Nullable. |
| `cr_returning_customer_sk` | `integer` | foreign key | Surrogate key to Customer; returning customer. Nullable. |
| `cr_returning_cdemo_sk` | `integer` | foreign key | Surrogate key to Customer Demographics; returning customer demographics. Nullable. |
| `cr_returning_hdemo_sk` | `integer` | foreign key | Surrogate key to Household Demographics; returning household demographics. Nullable. |
| `cr_returning_addr_sk` | `integer` | foreign key | Surrogate key to Customer Address; returning customer address. Nullable. |
| `cr_call_center_sk` | `integer` | foreign key | Surrogate key to Call Center; processing call center. Nullable. |
| `cr_catalog_page_sk` | `integer` | foreign key | Surrogate key to Catalog Page; catalog page. Nullable. |
| `cr_ship_mode_sk` | `integer` | foreign key | Surrogate key to Ship Mode; shipping mode. Nullable. |
| `cr_warehouse_sk` | `integer` | foreign key | Surrogate key to Warehouse; fulfillment warehouse. Nullable. |
| `cr_reason_sk` | `integer` | foreign key | Surrogate key to Return Reason; return reason. Nullable. |
| `cr_order_number` | `integer` | primary key | Surrogate key to Catalog Sales; matching catalog sale line. |
| `cr_return_quantity` | `integer` | additive measure | Number of units returned on the line. Nullable. |
| `cr_return_amount` | `decimal(7,2)` | additive measure | Returned merchandise amount. Nullable. |
| `cr_return_tax` | `decimal(7,2)` | additive measure | Tax amount associated with the return. Nullable. |
| `cr_return_amt_inc_tax` | `decimal(7,2)` | additive measure | Return amount including tax. Nullable. |
| `cr_fee` | `decimal(7,2)` | additive measure | Return fee charged for the line. Nullable. |
| `cr_return_ship_cost` | `decimal(7,2)` | additive measure | Shipping cost associated with the return. Nullable. |
| `cr_refunded_cash` | `decimal(7,2)` | attribute | Return value refunded as cash. Nullable. |
| `cr_reversed_charge` | `decimal(7,2)` | additive measure | Return value credited by reversing a charge. Nullable. |
| `cr_store_credit` | `decimal(7,2)` | additive measure | Return value issued as store credit. Nullable. |
| `cr_net_loss` | `decimal(7,2)` | additive measure | Net loss attributed to the returned line. Nullable. |

## Relationships

| Local columns | Target | Cardinality | Meaning |
| --- | --- | --- | --- |
| `cr_returned_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Return date. |
| `cr_returned_time_sk` | [time_dim](time_dim.md).`t_time_sk` | many-to-one | Return time. |
| `cr_item_sk` | [item](item.md).`i_item_sk` | many-to-one | Returned item. |
| `cr_refunded_customer_sk` | [customer](customer.md).`c_customer_sk` | many-to-one | Refunded customer. |
| `cr_refunded_cdemo_sk` | [customer_demographics](customer_demographics.md).`cd_demo_sk` | many-to-one | Refunded customer demographics. |
| `cr_refunded_hdemo_sk` | [household_demographics](household_demographics.md).`hd_demo_sk` | many-to-one | Refunded household demographics. |
| `cr_refunded_addr_sk` | [customer_address](customer_address.md).`ca_address_sk` | many-to-one | Refund address. |
| `cr_returning_customer_sk` | [customer](customer.md).`c_customer_sk` | many-to-one | Returning customer. |
| `cr_returning_cdemo_sk` | [customer_demographics](customer_demographics.md).`cd_demo_sk` | many-to-one | Returning customer demographics. |
| `cr_returning_hdemo_sk` | [household_demographics](household_demographics.md).`hd_demo_sk` | many-to-one | Returning household demographics. |
| `cr_returning_addr_sk` | [customer_address](customer_address.md).`ca_address_sk` | many-to-one | Returning customer address. |
| `cr_call_center_sk` | [call_center](call_center.md).`cc_call_center_sk` | many-to-one | Processing call center. |
| `cr_catalog_page_sk` | [catalog_page](catalog_page.md).`cp_catalog_page_sk` | many-to-one | Catalog page. |
| `cr_ship_mode_sk` | [ship_mode](ship_mode.md).`sm_ship_mode_sk` | many-to-one | Shipping mode. |
| `cr_warehouse_sk` | [warehouse](warehouse.md).`w_warehouse_sk` | many-to-one | Fulfillment warehouse. |
| `cr_reason_sk` | [reason](reason.md).`r_reason_sk` | many-to-one | Return reason. |
| `cr_item_sk`, `cr_order_number` | [catalog_sales](catalog_sales.md).`cs_item_sk`, `cs_order_number` | one-to-one (optional) | Matching catalog sale line. |

## Query guidance

- Join to catalog sales with both item key and order number.
- Returning-customer and refunded-customer roles are distinct.
- Return amounts and quantities are additive; unit-level interpretations must come from the matching sale line.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
