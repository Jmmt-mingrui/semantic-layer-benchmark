# Web Sales

Web order line items with billing, shipping, site/page, fulfillment, promotion, and financial measures.

## Semantic contract

- **Physical table:** `public.web_sales`
- **Kind:** fact
- **Domain:** web
- **Grain:** One web sales line per item and order number.
- **Primary key:** `ws_item_sk`, `ws_order_number`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `ws_sold_date_sk` | `integer` | foreign key | Surrogate key to Date; sale date. Nullable. |
| `ws_sold_time_sk` | `integer` | foreign key | Surrogate key to Time; sale time. Nullable. |
| `ws_ship_date_sk` | `integer` | foreign key | Surrogate key to Date; shipment date. Nullable. |
| `ws_item_sk` | `integer` | primary key | Surrogate key to Item; sold item. |
| `ws_bill_customer_sk` | `integer` | foreign key | Surrogate key to Customer; billing customer. Nullable. |
| `ws_bill_cdemo_sk` | `integer` | foreign key | Surrogate key to Customer Demographics; billing customer demographics. Nullable. |
| `ws_bill_hdemo_sk` | `integer` | foreign key | Surrogate key to Household Demographics; billing household demographics. Nullable. |
| `ws_bill_addr_sk` | `integer` | foreign key | Surrogate key to Customer Address; billing address. Nullable. |
| `ws_ship_customer_sk` | `integer` | foreign key | Surrogate key to Customer; shipping customer. Nullable. |
| `ws_ship_cdemo_sk` | `integer` | foreign key | Surrogate key to Customer Demographics; shipping customer demographics. Nullable. |
| `ws_ship_hdemo_sk` | `integer` | foreign key | Surrogate key to Household Demographics; shipping household demographics. Nullable. |
| `ws_ship_addr_sk` | `integer` | foreign key | Surrogate key to Customer Address; shipping address. Nullable. |
| `ws_web_page_sk` | `integer` | foreign key | Surrogate key to Web Page; web page. Nullable. |
| `ws_web_site_sk` | `integer` | foreign key | Surrogate key to Web Site; web site. Nullable. |
| `ws_ship_mode_sk` | `integer` | foreign key | Surrogate key to Ship Mode; shipping mode. Nullable. |
| `ws_warehouse_sk` | `integer` | foreign key | Surrogate key to Warehouse; fulfillment warehouse. Nullable. |
| `ws_promo_sk` | `integer` | foreign key | Surrogate key to Promotion; applied promotion. Nullable. |
| `ws_order_number` | `integer` | primary key | Primary-key component identifying the web sales row. |
| `ws_quantity` | `integer` | additive measure | Number of units sold on the line. Nullable. |
| `ws_wholesale_cost` | `decimal(7,2)` | non-additive measure | Wholesale cost per unit at the transaction. Nullable. |
| `ws_list_price` | `decimal(7,2)` | non-additive measure | List price per unit at the transaction. Nullable. |
| `ws_sales_price` | `decimal(7,2)` | non-additive measure | Actual selling price per unit at the transaction. Nullable. |
| `ws_ext_discount_amt` | `decimal(7,2)` | additive measure | Extended discount amount for the line. Nullable. |
| `ws_ext_sales_price` | `decimal(7,2)` | additive measure | Extended sales amount for the line. Nullable. |
| `ws_ext_wholesale_cost` | `decimal(7,2)` | additive measure | Extended wholesale cost for the line. Nullable. |
| `ws_ext_list_price` | `decimal(7,2)` | additive measure | Extended list-price amount for the line. Nullable. |
| `ws_ext_tax` | `decimal(7,2)` | additive measure | Extended tax amount for the line. Nullable. |
| `ws_coupon_amt` | `decimal(7,2)` | additive measure | Coupon discount amount applied to the line. Nullable. |
| `ws_ext_ship_cost` | `decimal(7,2)` | additive measure | Extended shipping cost for the line. Nullable. |
| `ws_net_paid` | `decimal(7,2)` | additive measure | Net amount paid before channel-specific tax or shipping additions. Nullable. |
| `ws_net_paid_inc_tax` | `decimal(7,2)` | additive measure | Net amount paid including tax. Nullable. |
| `ws_net_paid_inc_ship` | `decimal(7,2)` | additive measure | Net amount paid including shipping. Nullable. |
| `ws_net_paid_inc_ship_tax` | `decimal(7,2)` | additive measure | Net amount paid including shipping and tax. Nullable. |
| `ws_net_profit` | `decimal(7,2)` | additive measure | Net profit attributed to the line. Nullable. |

## Relationships

| Local columns | Target | Cardinality | Meaning |
| --- | --- | --- | --- |
| `ws_sold_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Sale date. |
| `ws_sold_time_sk` | [time_dim](time_dim.md).`t_time_sk` | many-to-one | Sale time. |
| `ws_ship_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Shipment date. |
| `ws_item_sk` | [item](item.md).`i_item_sk` | many-to-one | Sold item. |
| `ws_bill_customer_sk` | [customer](customer.md).`c_customer_sk` | many-to-one | Billing customer. |
| `ws_bill_cdemo_sk` | [customer_demographics](customer_demographics.md).`cd_demo_sk` | many-to-one | Billing customer demographics. |
| `ws_bill_hdemo_sk` | [household_demographics](household_demographics.md).`hd_demo_sk` | many-to-one | Billing household demographics. |
| `ws_bill_addr_sk` | [customer_address](customer_address.md).`ca_address_sk` | many-to-one | Billing address. |
| `ws_ship_customer_sk` | [customer](customer.md).`c_customer_sk` | many-to-one | Shipping customer. |
| `ws_ship_cdemo_sk` | [customer_demographics](customer_demographics.md).`cd_demo_sk` | many-to-one | Shipping customer demographics. |
| `ws_ship_hdemo_sk` | [household_demographics](household_demographics.md).`hd_demo_sk` | many-to-one | Shipping household demographics. |
| `ws_ship_addr_sk` | [customer_address](customer_address.md).`ca_address_sk` | many-to-one | Shipping address. |
| `ws_web_page_sk` | [web_page](web_page.md).`wp_web_page_sk` | many-to-one | Web page. |
| `ws_web_site_sk` | [web_site](web_site.md).`web_site_sk` | many-to-one | Web site. |
| `ws_ship_mode_sk` | [ship_mode](ship_mode.md).`sm_ship_mode_sk` | many-to-one | Shipping mode. |
| `ws_warehouse_sk` | [warehouse](warehouse.md).`w_warehouse_sk` | many-to-one | Fulfillment warehouse. |
| `ws_promo_sk` | [promotion](promotion.md).`p_promo_sk` | many-to-one | Applied promotion. |

## Query guidance

- Use role-specific billing and shipping dimension keys.
- Extended amounts and quantity are additive; unit prices and unit cost are not additive.
- Web page and web site are separate dimensions.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
