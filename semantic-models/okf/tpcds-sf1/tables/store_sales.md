---
type: PostgreSQL Table
title: Store Sales
description: Point-of-sale line items with customer context, promotion, store, and financial measures.
resource: urn:tpcds:sf1:postgresql:public:store_sales
tags: [tpc-ds-derived, sf1, store, fact]
status: draft
generated: { by: process:semantic-layer-benchmark, at: 2026-09-08T13:54:53Z }
table: public.store_sales
kind: fact
domain: store
grain: One store sales line per item and ticket number.
primary_key: [ss_item_sk, ss_ticket_number]
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

# Store Sales

Point-of-sale line items with customer context, promotion, store, and financial measures.

## Semantic contract

- **Physical table:** `public.store_sales`
- **Kind:** fact
- **Domain:** store
- **Grain:** One store sales line per item and ticket number.
- **Primary key:** `ss_item_sk`, `ss_ticket_number`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `ss_sold_date_sk` | `integer` | foreign key | Surrogate key to Date; sale date. Nullable. |
| `ss_sold_time_sk` | `integer` | foreign key | Surrogate key to Time; sale time. Nullable. |
| `ss_item_sk` | `integer` | primary key | Surrogate key to Item; sold item. |
| `ss_customer_sk` | `integer` | foreign key | Surrogate key to Customer; purchasing customer. Nullable. |
| `ss_cdemo_sk` | `integer` | foreign key | Surrogate key to Customer Demographics; customer demographics at sale. Nullable. |
| `ss_hdemo_sk` | `integer` | foreign key | Surrogate key to Household Demographics; household demographics at sale. Nullable. |
| `ss_addr_sk` | `integer` | foreign key | Surrogate key to Customer Address; customer address at sale. Nullable. |
| `ss_store_sk` | `integer` | foreign key | Surrogate key to Store; selling store. Nullable. |
| `ss_promo_sk` | `integer` | foreign key | Surrogate key to Promotion; applied promotion. Nullable. |
| `ss_ticket_number` | `integer` | primary key | Primary-key component identifying the store sales row. |
| `ss_quantity` | `integer` | additive measure | Number of units sold on the line. Nullable. |
| `ss_wholesale_cost` | `decimal(7,2)` | non-additive measure | Wholesale cost per unit at the transaction. Nullable. |
| `ss_list_price` | `decimal(7,2)` | non-additive measure | List price per unit at the transaction. Nullable. |
| `ss_sales_price` | `decimal(7,2)` | non-additive measure | Actual selling price per unit at the transaction. Nullable. |
| `ss_ext_discount_amt` | `decimal(7,2)` | additive measure | Extended discount amount for the line. Nullable. |
| `ss_ext_sales_price` | `decimal(7,2)` | additive measure | Extended sales amount for the line. Nullable. |
| `ss_ext_wholesale_cost` | `decimal(7,2)` | additive measure | Extended wholesale cost for the line. Nullable. |
| `ss_ext_list_price` | `decimal(7,2)` | additive measure | Extended list-price amount for the line. Nullable. |
| `ss_ext_tax` | `decimal(7,2)` | additive measure | Extended tax amount for the line. Nullable. |
| `ss_coupon_amt` | `decimal(7,2)` | additive measure | Coupon discount amount applied to the line. Nullable. |
| `ss_net_paid` | `decimal(7,2)` | additive measure | Net amount paid before channel-specific tax or shipping additions. Nullable. |
| `ss_net_paid_inc_tax` | `decimal(7,2)` | additive measure | Net amount paid including tax. Nullable. |
| `ss_net_profit` | `decimal(7,2)` | additive measure | Net profit attributed to the line. Nullable. |

## Relationships

| Local columns | Target | Cardinality | Meaning |
| --- | --- | --- | --- |
| `ss_sold_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Sale date. |
| `ss_sold_time_sk` | [time_dim](time_dim.md).`t_time_sk` | many-to-one | Sale time. |
| `ss_item_sk` | [item](item.md).`i_item_sk` | many-to-one | Sold item. |
| `ss_customer_sk` | [customer](customer.md).`c_customer_sk` | many-to-one | Purchasing customer. |
| `ss_cdemo_sk` | [customer_demographics](customer_demographics.md).`cd_demo_sk` | many-to-one | Customer demographics at sale. |
| `ss_hdemo_sk` | [household_demographics](household_demographics.md).`hd_demo_sk` | many-to-one | Household demographics at sale. |
| `ss_addr_sk` | [customer_address](customer_address.md).`ca_address_sk` | many-to-one | Customer address at sale. |
| `ss_store_sk` | [store](store.md).`s_store_sk` | many-to-one | Selling store. |
| `ss_promo_sk` | [promotion](promotion.md).`p_promo_sk` | many-to-one | Applied promotion. |

## Query guidance

- Ticket number alone is not the line key; pair it with item key.
- Extended amounts and quantity are additive; unit prices and unit cost are not additive.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
