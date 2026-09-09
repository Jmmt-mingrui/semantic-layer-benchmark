# Base metric families

Reusable physical aggregations. Select the named variant for the requested sales channel or fact role.

Source of truth: `semantic-models/canonical/tpcds-sf1/metrics.yaml`.

```yaml
metric_families:
- id: sales_revenue
  label: Sales revenue
  kind: base
  value_type: currency
  additivity: additive
  definition: Sum of the channel's extended sales price at sales-line grain.
  variants:
    store:
      dataset: store_sales
      expression: SUM(ss_ext_sales_price)
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_ext_sales_price)
    web:
      dataset: web_sales
      expression: SUM(ws_ext_sales_price)
- id: sales_price_sum
  label: Sales price sum
  kind: base
  value_type: currency
  additivity: query_defined
  definition: Sum of the per-line sales-price column. Kept distinct from sales revenue.
  variants:
    store:
      dataset: store_sales
      expression: SUM(ss_sales_price)
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_sales_price)
    web:
      dataset: web_sales
      expression: SUM(ws_sales_price)
- id: list_value_sales
  label: Quantity-weighted list value
  kind: base_expression
  value_type: currency
  additivity: additive
  definition: Sum of quantity multiplied by list price.
  variants:
    store:
      dataset: store_sales
      expression: SUM(ss_quantity * ss_list_price)
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_quantity * cs_list_price)
    web:
      dataset: web_sales
      expression: SUM(ws_quantity * ws_list_price)
- id: gross_sales_value
  label: Quantity-weighted sales value
  kind: base_expression
  value_type: currency
  additivity: additive
  definition: Sum of quantity multiplied by sales price.
  variants:
    store:
      dataset: store_sales
      expression: SUM(ss_quantity * ss_sales_price)
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_quantity * cs_sales_price)
    web:
      dataset: web_sales
      expression: SUM(ws_quantity * ws_sales_price)
- id: sales_quantity
  label: Sales quantity
  kind: base
  value_type: quantity
  additivity: additive
  variants:
    store:
      dataset: store_sales
      expression: SUM(ss_quantity)
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_quantity)
    web:
      dataset: web_sales
      expression: SUM(ws_quantity)
- id: list_price_sum
  label: List price sum
  kind: base
  value_type: currency
  additivity: query_defined
  definition: Sum of unit list prices; retained only because benchmark queries use it directly.
  variants:
    store:
      dataset: store_sales
      expression: SUM(ss_list_price)
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_list_price)
    web:
      dataset: web_sales
      expression: SUM(ws_list_price)
- id: wholesale_cost_sum
  label: Wholesale cost sum
  kind: base
  value_type: currency
  additivity: query_defined
  definition: Sum of unit wholesale-cost values; not a generally additive revenue measure.
  variants:
    store:
      dataset: store_sales
      expression: SUM(ss_wholesale_cost)
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_wholesale_cost)
    web:
      dataset: web_sales
      expression: SUM(ws_wholesale_cost)
- id: extended_wholesale_cost
  label: Extended wholesale cost
  kind: base
  value_type: currency
  additivity: additive
  variants:
    store:
      dataset: store_sales
      expression: SUM(ss_ext_wholesale_cost)
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_ext_wholesale_cost)
    web:
      dataset: web_sales
      expression: SUM(ws_ext_wholesale_cost)
- id: extended_list_price
  label: Extended list price
  kind: base
  value_type: currency
  additivity: additive
  variants:
    store:
      dataset: store_sales
      expression: SUM(ss_ext_list_price)
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_ext_list_price)
    web:
      dataset: web_sales
      expression: SUM(ws_ext_list_price)
- id: sales_after_discount
  label: Extended list price after discount
  kind: base_expression
  value_type: currency
  additivity: additive
  variants:
    store:
      dataset: store_sales
      expression: SUM(ss_ext_list_price - ss_ext_discount_amt)
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_ext_list_price - cs_ext_discount_amt)
    web:
      dataset: web_sales
      expression: SUM(ws_ext_list_price - ws_ext_discount_amt)
- id: net_paid
  label: Net paid
  kind: base
  value_type: currency
  additivity: additive
  variants:
    store:
      dataset: store_sales
      expression: SUM(ss_net_paid)
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_net_paid)
    web:
      dataset: web_sales
      expression: SUM(ws_net_paid)
- id: net_profit
  label: Net profit
  kind: base
  value_type: currency
  additivity: additive
  variants:
    store:
      dataset: store_sales
      expression: SUM(ss_net_profit)
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_net_profit)
    web:
      dataset: web_sales
      expression: SUM(ws_net_profit)
- id: discount_amount
  label: Extended discount amount
  kind: base
  value_type: currency
  additivity: additive
  variants:
    store:
      dataset: store_sales
      expression: SUM(ss_ext_discount_amt)
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_ext_discount_amt)
    web:
      dataset: web_sales
      expression: SUM(ws_ext_discount_amt)
- id: coupon_amount
  label: Coupon amount
  kind: base
  value_type: currency
  additivity: additive
  variants:
    store:
      dataset: store_sales
      expression: SUM(ss_coupon_amt)
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_coupon_amt)
    web:
      dataset: web_sales
      expression: SUM(ws_coupon_amt)
- id: extended_tax
  label: Extended sales tax
  kind: base
  value_type: currency
  additivity: additive
  variants:
    store:
      dataset: store_sales
      expression: SUM(ss_ext_tax)
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_ext_tax)
    web:
      dataset: web_sales
      expression: SUM(ws_ext_tax)
- id: shipping_cost
  label: Extended shipping cost
  kind: base
  value_type: currency
  additivity: additive
  variants:
    catalog:
      dataset: catalog_sales
      expression: SUM(cs_ext_ship_cost)
    web:
      dataset: web_sales
      expression: SUM(ws_ext_ship_cost)
- id: return_amount
  label: Return amount
  kind: base
  value_type: currency
  additivity: additive
  variants:
    store:
      dataset: store_returns
      expression: SUM(sr_return_amt)
    catalog:
      dataset: catalog_returns
      expression: SUM(cr_return_amount)
    web:
      dataset: web_returns
      expression: SUM(wr_return_amt)
- id: return_amount_including_tax
  label: Return amount including tax
  kind: base
  value_type: currency
  additivity: additive
  variants:
    store:
      dataset: store_returns
      expression: SUM(sr_return_amt_inc_tax)
    catalog:
      dataset: catalog_returns
      expression: SUM(cr_return_amt_inc_tax)
    web:
      dataset: web_returns
      expression: SUM(wr_return_amt_inc_tax)
- id: return_quantity
  label: Return quantity
  kind: base
  value_type: quantity
  additivity: additive
  variants:
    store:
      dataset: store_returns
      expression: SUM(sr_return_quantity)
    catalog:
      dataset: catalog_returns
      expression: SUM(cr_return_quantity)
    web:
      dataset: web_returns
      expression: SUM(wr_return_quantity)
- id: return_net_loss
  label: Return net loss
  kind: base
  value_type: currency
  additivity: additive
  variants:
    store:
      dataset: store_returns
      expression: SUM(sr_net_loss)
    catalog:
      dataset: catalog_returns
      expression: SUM(cr_net_loss)
    web:
      dataset: web_returns
      expression: SUM(wr_net_loss)
- id: refunded_cash
  label: Refunded cash
  kind: base
  value_type: currency
  additivity: additive
  variants:
    store:
      dataset: store_returns
      expression: SUM(sr_refunded_cash)
    catalog:
      dataset: catalog_returns
      expression: SUM(cr_refunded_cash)
    web:
      dataset: web_returns
      expression: SUM(wr_refunded_cash)
- id: return_fee
  label: Return fee
  kind: base
  value_type: currency
  additivity: additive
  variants:
    store:
      dataset: store_returns
      expression: SUM(sr_fee)
    catalog:
      dataset: catalog_returns
      expression: SUM(cr_fee)
    web:
      dataset: web_returns
      expression: SUM(wr_fee)
- id: inventory_quantity_on_hand
  label: Inventory quantity on hand
  kind: base
  value_type: quantity
  additivity: semi_additive
  default_aggregation: none
  constraint: May aggregate across items or warehouses at one snapshot, but not blindly across dates.
  variants:
    inventory:
      dataset: inventory
      expression: inv_quantity_on_hand
- id: sales_row_count
  label: Sales row count
  kind: count
  value_type: count
  additivity: additive
  variants:
    store:
      dataset: store_sales
      expression: COUNT(*)
    catalog:
      dataset: catalog_sales
      expression: COUNT(*)
    web:
      dataset: web_sales
      expression: COUNT(*)
- id: distinct_order_count
  label: Distinct order count
  kind: count_distinct
  value_type: count
  additivity: non_additive
  variants:
    catalog:
      dataset: catalog_sales
      expression: COUNT(DISTINCT cs_order_number)
    web:
      dataset: web_sales
      expression: COUNT(DISTINCT ws_order_number)
- id: customer_count
  label: Customer count
  kind: count_distinct
  value_type: count
  additivity: non_additive
  definition: Distinct customers after the question-specific channel and date constraints.
- id: item_count
  label: Item count
  kind: count_distinct
  value_type: count
  additivity: non_additive
- id: non_null_value_count
  label: Non-null value count
  kind: count
  value_type: count
  additivity: additive
  expression: COUNT(<field>)
- id: distinct_value_count
  label: Distinct value count
  kind: count_distinct
  value_type: count
  additivity: non_additive
  expression: COUNT(DISTINCT <field>)
- id: average_sales_quantity
  label: Average sales quantity
  kind: average
  value_type: quantity
  additivity: non_additive
  variants:
    store:
      dataset: store_sales
      expression: AVG(ss_quantity)
    catalog:
      dataset: catalog_sales
      expression: AVG(cs_quantity)
    web:
      dataset: web_sales
      expression: AVG(ws_quantity)
- id: average_return_quantity
  label: Average return quantity
  kind: average
  value_type: quantity
  additivity: non_additive
  variants:
    store:
      dataset: store_returns
      expression: AVG(sr_return_quantity)
    catalog:
      dataset: catalog_returns
      expression: AVG(cr_return_quantity)
    web:
      dataset: web_returns
      expression: AVG(wr_return_quantity)
- id: average_list_price
  label: Average list price
  kind: average
  value_type: currency
  additivity: non_additive
  variants:
    store:
      dataset: store_sales
      expression: AVG(ss_list_price)
    catalog:
      dataset: catalog_sales
      expression: AVG(cs_list_price)
    web:
      dataset: web_sales
      expression: AVG(ws_list_price)
- id: average_coupon_amount
  label: Average coupon amount
  kind: average
  value_type: currency
  additivity: non_additive
  variants:
    store:
      dataset: store_sales
      expression: AVG(ss_coupon_amt)
    catalog:
      dataset: catalog_sales
      expression: AVG(cs_coupon_amt)
    web:
      dataset: web_sales
      expression: AVG(ws_coupon_amt)
- id: average_sales_price
  label: Average sales price
  kind: average
  value_type: currency
  additivity: non_additive
  variants:
    store:
      dataset: store_sales
      expression: AVG(ss_sales_price)
    catalog:
      dataset: catalog_sales
      expression: AVG(cs_sales_price)
    web:
      dataset: web_sales
      expression: AVG(ws_sales_price)
- id: average_net_profit
  label: Average net profit
  kind: average
  value_type: currency
  additivity: non_additive
  variants:
    store:
      dataset: store_sales
      expression: AVG(ss_net_profit)
    catalog:
      dataset: catalog_sales
      expression: AVG(cs_net_profit)
    web:
      dataset: web_sales
      expression: AVG(ws_net_profit)
- id: average_extended_sales_price
  label: Average extended sales price
  kind: average
  value_type: currency
  additivity: non_additive
  variants:
    store:
      dataset: store_sales
      expression: AVG(ss_ext_sales_price)
    catalog:
      dataset: catalog_sales
      expression: AVG(cs_ext_sales_price)
    web:
      dataset: web_sales
      expression: AVG(ws_ext_sales_price)
- id: average_extended_wholesale_cost
  label: Average extended wholesale cost
  kind: average
  value_type: currency
  additivity: non_additive
  variants:
    store:
      dataset: store_sales
      expression: AVG(ss_ext_wholesale_cost)
    catalog:
      dataset: catalog_sales
      expression: AVG(cs_ext_wholesale_cost)
    web:
      dataset: web_sales
      expression: AVG(ws_ext_wholesale_cost)
- id: average_extended_discount_amount
  label: Average extended discount amount
  kind: average
  value_type: currency
  additivity: non_additive
  variants:
    store:
      dataset: store_sales
      expression: AVG(ss_ext_discount_amt)
    catalog:
      dataset: catalog_sales
      expression: AVG(cs_ext_discount_amt)
    web:
      dataset: web_sales
      expression: AVG(ws_ext_discount_amt)
- id: average_net_paid
  label: Average net paid
  kind: average
  value_type: currency
  additivity: non_additive
  variants:
    store:
      dataset: store_sales
      expression: AVG(ss_net_paid)
    catalog:
      dataset: catalog_sales
      expression: AVG(cs_net_paid)
    web:
      dataset: web_sales
      expression: AVG(ws_net_paid)
- id: average_inventory_quantity
  label: Average inventory quantity on hand
  kind: average
  value_type: quantity
  additivity: non_additive
  expression: AVG(inventory.inv_quantity_on_hand)
- id: quantity_stddev
  label: Quantity sample standard deviation
  kind: standard_deviation
  value_type: quantity
  additivity: non_additive
  variants:
    store_sales:
      dataset: store_sales
      expression: STDDEV_SAMP(ss_quantity)
    catalog_sales:
      dataset: catalog_sales
      expression: STDDEV_SAMP(cs_quantity)
    web_sales:
      dataset: web_sales
      expression: STDDEV_SAMP(ws_quantity)
    store_returns:
      dataset: store_returns
      expression: STDDEV_SAMP(sr_return_quantity)
    catalog_returns:
      dataset: catalog_returns
      expression: STDDEV_SAMP(cr_return_quantity)
    web_returns:
      dataset: web_returns
      expression: STDDEV_SAMP(wr_return_quantity)
- id: inventory_quantity_stddev
  label: Inventory quantity standard deviation
  kind: standard_deviation
  value_type: quantity
  additivity: non_additive
  expression: STDDEV_SAMP(inventory.inv_quantity_on_hand)
```

