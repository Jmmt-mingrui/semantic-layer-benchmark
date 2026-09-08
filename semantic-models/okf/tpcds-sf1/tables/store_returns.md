---
type: PostgreSQL Table
title: Store Returns
description: Returned store line items with customer context, reason, refund disposition, and net loss.
resource: urn:tpcds:sf1:postgresql:public:store_returns
tags: [tpc-ds-derived, sf1, store, fact]
status: draft
generated: { by: process:semantic-layer-benchmark, at: 2026-09-08T13:54:53Z }
table: public.store_returns
kind: fact
domain: store
grain: One returned store line item per item and ticket number.
primary_key: [sr_item_sk, sr_ticket_number]
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

# Store Returns

Returned store line items with customer context, reason, refund disposition, and net loss.

## Semantic contract

- **Physical table:** `public.store_returns`
- **Kind:** fact
- **Domain:** store
- **Grain:** One returned store line item per item and ticket number.
- **Primary key:** `sr_item_sk`, `sr_ticket_number`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `sr_returned_date_sk` | `integer` | foreign key | Surrogate key to Date; return date. Nullable. |
| `sr_return_time_sk` | `integer` | foreign key | Surrogate key to Time; return time. Nullable. |
| `sr_item_sk` | `integer` | primary key | Surrogate key to Store Sales; matching store sale line. |
| `sr_customer_sk` | `integer` | foreign key | Surrogate key to Customer; returning customer. Nullable. |
| `sr_cdemo_sk` | `integer` | foreign key | Surrogate key to Customer Demographics; customer demographics at return. Nullable. |
| `sr_hdemo_sk` | `integer` | foreign key | Surrogate key to Household Demographics; household demographics at return. Nullable. |
| `sr_addr_sk` | `integer` | foreign key | Surrogate key to Customer Address; customer address at return. Nullable. |
| `sr_store_sk` | `integer` | foreign key | Surrogate key to Store; return store. Nullable. |
| `sr_reason_sk` | `integer` | foreign key | Surrogate key to Return Reason; return reason. Nullable. |
| `sr_ticket_number` | `integer` | primary key | Surrogate key to Store Sales; matching store sale line. |
| `sr_return_quantity` | `integer` | additive measure | Number of units returned on the line. Nullable. |
| `sr_return_amt` | `decimal(7,2)` | additive measure | Returned merchandise amount. Nullable. |
| `sr_return_tax` | `decimal(7,2)` | additive measure | Tax amount associated with the return. Nullable. |
| `sr_return_amt_inc_tax` | `decimal(7,2)` | additive measure | Return amount including tax. Nullable. |
| `sr_fee` | `decimal(7,2)` | additive measure | Return fee charged for the line. Nullable. |
| `sr_return_ship_cost` | `decimal(7,2)` | additive measure | Shipping cost associated with the return. Nullable. |
| `sr_refunded_cash` | `decimal(7,2)` | attribute | Return value refunded as cash. Nullable. |
| `sr_reversed_charge` | `decimal(7,2)` | additive measure | Return value credited by reversing a charge. Nullable. |
| `sr_store_credit` | `decimal(7,2)` | additive measure | Return value issued as store credit. Nullable. |
| `sr_net_loss` | `decimal(7,2)` | additive measure | Net loss attributed to the returned line. Nullable. |

## Relationships

| Local columns | Target | Cardinality | Meaning |
| --- | --- | --- | --- |
| `sr_returned_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Return date. |
| `sr_return_time_sk` | [time_dim](time_dim.md).`t_time_sk` | many-to-one | Return time. |
| `sr_item_sk` | [item](item.md).`i_item_sk` | many-to-one | Returned item. |
| `sr_customer_sk` | [customer](customer.md).`c_customer_sk` | many-to-one | Returning customer. |
| `sr_cdemo_sk` | [customer_demographics](customer_demographics.md).`cd_demo_sk` | many-to-one | Customer demographics at return. |
| `sr_hdemo_sk` | [household_demographics](household_demographics.md).`hd_demo_sk` | many-to-one | Household demographics at return. |
| `sr_addr_sk` | [customer_address](customer_address.md).`ca_address_sk` | many-to-one | Customer address at return. |
| `sr_store_sk` | [store](store.md).`s_store_sk` | many-to-one | Return store. |
| `sr_reason_sk` | [reason](reason.md).`r_reason_sk` | many-to-one | Return reason. |
| `sr_item_sk`, `sr_ticket_number` | [store_sales](store_sales.md).`ss_item_sk`, `ss_ticket_number` | one-to-one (optional) | Matching store sale line. |

## Query guidance

- Join to store sales with both item key and ticket number.
- Return quantities and financial effects are additive across return rows.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
