# Catalog Sales

Catalog order line items with billing, shipping, fulfillment, promotion, and financial measures.

## Semantic contract

- **Physical table:** `public.catalog_sales`
- **Kind:** fact
- **Domain:** catalog
- **Grain:** One catalog sales line per item and order number.
- **Primary key:** `cs_item_sk`, `cs_order_number`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `cs_sold_date_sk` | `integer` | foreign key | Surrogate key to Date; sale date. Nullable. |
| `cs_sold_time_sk` | `integer` | foreign key | Surrogate key to Time; sale time. Nullable. |
| `cs_ship_date_sk` | `integer` | foreign key | Surrogate key to Date; shipment date. Nullable. |
| `cs_bill_customer_sk` | `integer` | foreign key | Surrogate key to Customer; billing customer. Nullable. |
| `cs_bill_cdemo_sk` | `integer` | foreign key | Surrogate key to Customer Demographics; billing customer demographics. Nullable. |
| `cs_bill_hdemo_sk` | `integer` | foreign key | Surrogate key to Household Demographics; billing household demographics. Nullable. |
| `cs_bill_addr_sk` | `integer` | foreign key | Surrogate key to Customer Address; billing address. Nullable. |
| `cs_ship_customer_sk` | `integer` | foreign key | Surrogate key to Customer; shipping customer. Nullable. |
| `cs_ship_cdemo_sk` | `integer` | foreign key | Surrogate key to Customer Demographics; shipping customer demographics. Nullable. |
| `cs_ship_hdemo_sk` | `integer` | foreign key | Surrogate key to Household Demographics; shipping household demographics. Nullable. |
| `cs_ship_addr_sk` | `integer` | foreign key | Surrogate key to Customer Address; shipping address. Nullable. |
| `cs_call_center_sk` | `integer` | foreign key | Surrogate key to Call Center; originating call center. Nullable. |
| `cs_catalog_page_sk` | `integer` | foreign key | Surrogate key to Catalog Page; catalog page. Nullable. |
| `cs_ship_mode_sk` | `integer` | foreign key | Surrogate key to Ship Mode; shipping mode. Nullable. |
| `cs_warehouse_sk` | `integer` | foreign key | Surrogate key to Warehouse; fulfillment warehouse. Nullable. |
| `cs_item_sk` | `integer` | primary key | Surrogate key to Item; sold item. |
| `cs_promo_sk` | `integer` | foreign key | Surrogate key to Promotion; applied promotion. Nullable. |
| `cs_order_number` | `integer` | primary key | Primary-key component identifying the catalog sales row. |
| `cs_quantity` | `integer` | additive measure | Number of units sold on the line. Nullable. |
| `cs_wholesale_cost` | `decimal(7,2)` | non-additive measure | Wholesale cost per unit at the transaction. Nullable. |
| `cs_list_price` | `decimal(7,2)` | non-additive measure | List price per unit at the transaction. Nullable. |
| `cs_sales_price` | `decimal(7,2)` | non-additive measure | Actual selling price per unit at the transaction. Nullable. |
| `cs_ext_discount_amt` | `decimal(7,2)` | additive measure | Extended discount amount for the line. Nullable. |
| `cs_ext_sales_price` | `decimal(7,2)` | additive measure | Extended sales amount for the line. Nullable. |
| `cs_ext_wholesale_cost` | `decimal(7,2)` | additive measure | Extended wholesale cost for the line. Nullable. |
| `cs_ext_list_price` | `decimal(7,2)` | additive measure | Extended list-price amount for the line. Nullable. |
| `cs_ext_tax` | `decimal(7,2)` | additive measure | Extended tax amount for the line. Nullable. |
| `cs_coupon_amt` | `decimal(7,2)` | additive measure | Coupon discount amount applied to the line. Nullable. |
| `cs_ext_ship_cost` | `decimal(7,2)` | additive measure | Extended shipping cost for the line. Nullable. |
| `cs_net_paid` | `decimal(7,2)` | additive measure | Net amount paid before channel-specific tax or shipping additions. Nullable. |
| `cs_net_paid_inc_tax` | `decimal(7,2)` | additive measure | Net amount paid including tax. Nullable. |
| `cs_net_paid_inc_ship` | `decimal(7,2)` | additive measure | Net amount paid including shipping. Nullable. |
| `cs_net_paid_inc_ship_tax` | `decimal(7,2)` | additive measure | Net amount paid including shipping and tax. Nullable. |
| `cs_net_profit` | `decimal(7,2)` | additive measure | Net profit attributed to the line. Nullable. |

## Relationships

| Local columns | Target | Cardinality | Meaning |
| --- | --- | --- | --- |
| `cs_sold_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Sale date. |
| `cs_sold_time_sk` | [time_dim](time_dim.md).`t_time_sk` | many-to-one | Sale time. |
| `cs_ship_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Shipment date. |
| `cs_bill_customer_sk` | [customer](customer.md).`c_customer_sk` | many-to-one | Billing customer. |
| `cs_bill_cdemo_sk` | [customer_demographics](customer_demographics.md).`cd_demo_sk` | many-to-one | Billing customer demographics. |
| `cs_bill_hdemo_sk` | [household_demographics](household_demographics.md).`hd_demo_sk` | many-to-one | Billing household demographics. |
| `cs_bill_addr_sk` | [customer_address](customer_address.md).`ca_address_sk` | many-to-one | Billing address. |
| `cs_ship_customer_sk` | [customer](customer.md).`c_customer_sk` | many-to-one | Shipping customer. |
| `cs_ship_cdemo_sk` | [customer_demographics](customer_demographics.md).`cd_demo_sk` | many-to-one | Shipping customer demographics. |
| `cs_ship_hdemo_sk` | [household_demographics](household_demographics.md).`hd_demo_sk` | many-to-one | Shipping household demographics. |
| `cs_ship_addr_sk` | [customer_address](customer_address.md).`ca_address_sk` | many-to-one | Shipping address. |
| `cs_call_center_sk` | [call_center](call_center.md).`cc_call_center_sk` | many-to-one | Originating call center. |
| `cs_catalog_page_sk` | [catalog_page](catalog_page.md).`cp_catalog_page_sk` | many-to-one | Catalog page. |
| `cs_ship_mode_sk` | [ship_mode](ship_mode.md).`sm_ship_mode_sk` | many-to-one | Shipping mode. |
| `cs_warehouse_sk` | [warehouse](warehouse.md).`w_warehouse_sk` | many-to-one | Fulfillment warehouse. |
| `cs_item_sk` | [item](item.md).`i_item_sk` | many-to-one | Sold item. |
| `cs_promo_sk` | [promotion](promotion.md).`p_promo_sk` | many-to-one | Applied promotion. |

## Query guidance

- Use role-specific billing and shipping dimension keys.
- Extended amounts and quantity are additive; unit prices and unit cost are not additive.
- Use ship date for fulfillment timing and sold date for demand timing.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
