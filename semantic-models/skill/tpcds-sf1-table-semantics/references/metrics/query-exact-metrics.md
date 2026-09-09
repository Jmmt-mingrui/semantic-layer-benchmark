# Query-exact metrics

TPC-DS-specific formulas that must remain exact and must not be presented as general-purpose business KPIs.

Source of truth: `semantic-models/canonical/tpcds-sf1/metrics.yaml`.

```yaml
query_exact_metrics:
- id: q04_customer_spend_proxy
  label: Query 04 customer spend proxy
  value_type: currency
  warning: This benchmark formula is not equivalent to standard revenue or net-paid metrics.
  variants:
    store: SUM(((ss_ext_list_price - ss_ext_wholesale_cost - ss_ext_discount_amt) + ss_ext_sales_price) / 2)
    catalog: SUM(((cs_ext_list_price - cs_ext_wholesale_cost - cs_ext_discount_amt) + cs_ext_sales_price) / 2)
    web: SUM(((ws_ext_list_price - ws_ext_wholesale_cost - ws_ext_discount_amt) + ws_ext_sales_price) / 2)
- id: q14_average_line_list_value
  label: Query 14 average line list value
  expression: AVG(quantity * list_price) across unioned channel lines
- id: q21_inventory_before_after_quantity
  label: Query 21 inventory quantity before and after price change
  expression: Conditional SUM(inv_quantity_on_hand) on each side of PRICE_CHANGE_DATE
- id: q40_catalog_net_sales_before_after
  label: Query 40 catalog sales net of refunded cash before and after price change
  expression: Conditional SUM(cs_sales_price - COALESCE(cr_refunded_cash, 0))
- id: q64_catalog_sale_to_refund_ratio
  label: Query 64 catalog sale-to-refund qualification
  expression: SUM(cs_ext_list_price) / NULLIF(SUM(cr_refunded_cash + cr_reversed_charge + cr_store_credit), 0)
- id: q66_warehouse_monthly_sales_value
  label: Query 66 warehouse monthly sales value
  warning: Preserves the benchmark's quantity multiplication exactly.
  variants:
    web: SUM(ws_ext_sales_price * ws_quantity)
    catalog: SUM(cs_sales_price * cs_quantity)
- id: q66_warehouse_monthly_net_value
  label: Query 66 warehouse monthly net value
  warning: Preserves the benchmark's quantity multiplication exactly.
  variants:
    web: SUM(ws_net_paid * ws_quantity)
    catalog: SUM(cs_net_paid_inc_tax * cs_quantity)
- id: q85_average_web_return_values
  label: Query 85 average web return values
  expressions:
    average_web_sales_quantity: AVG(ws_quantity)
    average_refunded_cash: AVG(wr_refunded_cash)
    average_return_fee: AVG(wr_fee)
- id: q93_actual_store_sales_after_return
  label: Query 93 store sales value after returned quantity
  expression: SUM((ss_quantity - COALESCE(sr_return_quantity, 0)) * ss_sales_price)
```

