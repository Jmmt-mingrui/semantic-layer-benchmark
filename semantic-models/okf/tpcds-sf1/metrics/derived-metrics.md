---
type: Metric Catalog
title: Derived Metrics
description: Reusable metric arithmetic over compatible base metric grains.
resource: urn:tpcds:sf1:metrics:derived-metrics
tags:
- tpc-ds-derived
- sf1
- metrics
status: draft
sources:
- id: canonical-metrics
  resource: ../../../canonical/tpcds-sf1/metrics.yaml
  title: Canonical TPC-DS SF1 metric contract
  author: process:semantic-layer-benchmark
---

# Derived Metrics

Reusable metric arithmetic over compatible base metric grains.

The identifiers and formulas below are copied from the canonical contract so OKF consumers can retrieve them as a native knowledge concept.

```yaml
derived_metrics:
- id: all_channel_sales_revenue
  label: All-channel sales revenue
  kind: derived
  value_type: currency
  expression: sales_revenue.store + sales_revenue.catalog + sales_revenue.web
- id: all_channel_sales_quantity
  label: All-channel sales quantity
  kind: derived
  value_type: quantity
  expression: sales_quantity.store + sales_quantity.catalog + sales_quantity.web
- id: all_channel_return_amount
  label: All-channel return amount
  kind: derived
  value_type: currency
  expression: return_amount.store + return_amount.catalog + return_amount.web
- id: all_channel_return_quantity
  label: All-channel return quantity
  kind: derived
  value_type: quantity
  expression: return_quantity.store + return_quantity.catalog + return_quantity.web
- id: all_channel_net_profit
  label: All-channel net profit
  kind: derived
  value_type: currency
  expression: net_profit.store + net_profit.catalog + net_profit.web
- id: all_channel_return_net_loss
  label: All-channel return net loss
  kind: derived
  value_type: currency
  expression: return_net_loss.store + return_net_loss.catalog + return_net_loss.web
- id: net_sales_amount
  label: Net sales amount after returns
  kind: derived_template
  value_type: currency
  expression: sales_revenue.<channel> - COALESCE(return_amount.<channel>, 0)
- id: net_sales_quantity
  label: Net sales quantity after returns
  kind: derived_template
  value_type: quantity
  expression: sales_quantity.<channel> - COALESCE(return_quantity.<channel>, 0)
- id: net_profit_after_return_loss
  label: Net profit after return loss
  kind: derived_template
  value_type: currency
  expression: net_profit.<channel> - COALESCE(return_net_loss.<channel>, 0)
- id: sales_share_pct
  label: Sales share
  kind: ratio
  value_type: percentage
  expression: 100 * selected_sales / parent_total_sales
- id: growth_ratio
  label: Period-over-period growth ratio
  kind: ratio
  value_type: ratio
  expression: current_period_value / NULLIF(previous_period_value, 0)
- id: growth_delta
  label: Period-over-period absolute change
  kind: derived_template
  expression: current_period_value - previous_period_value
- id: gross_margin_ratio
  label: Gross profit margin
  kind: ratio
  value_type: ratio
  expression: net_profit / NULLIF(sales_revenue, 0)
- id: return_ratio_quantity
  label: Return ratio by quantity
  kind: ratio
  value_type: ratio
  expression: return_quantity / NULLIF(sales_quantity, 0)
- id: return_ratio_amount
  label: Return ratio by amount
  kind: ratio
  value_type: ratio
  expression: return_amount / NULLIF(net_paid, 0)
- id: promotion_sales_share_pct
  label: Promotional sales share
  kind: ratio
  value_type: percentage
  expression: 100 * promotional_sales_revenue / NULLIF(all_sales_revenue, 0)
- id: monthly_average
  label: Average monthly value
  kind: window_average
  expression: AVG(monthly_value) OVER (PARTITION BY yearly_parent_grain)
- id: deviation_from_average_pct
  label: Percentage deviation from average
  kind: ratio
  value_type: percentage
  expression: 100 * (value - average_value) / NULLIF(average_value, 0)
- id: coefficient_of_variation_pct
  label: Coefficient of variation
  kind: ratio
  value_type: percentage
  expression: 100 * inventory_quantity_stddev / NULLIF(average_inventory_quantity, 0)
- id: inventory_change_pct
  label: Inventory percentage change
  kind: ratio
  value_type: percentage
  expression: 100 * (after_quantity - before_quantity) / NULLIF(before_quantity, 0)
- id: sales_per_square_foot
  label: Sales per square foot
  kind: ratio
  expression: sales_value / NULLIF(warehouse_square_feet, 0)
- id: elapsed_days_bucket_count
  label: Elapsed-days bucket count
  kind: conditional_count
  value_type: count
  buckets:
  - up_to_30_days
  - 31_to_60_days
  - 61_to_90_days
  - 91_to_120_days
  - over_120_days
- id: time_window_count_ratio
  label: Time-window count ratio
  kind: ratio
  value_type: ratio
  expression: first_window_count / NULLIF(second_window_count, 0)
- id: channel_overlap_count
  label: Channel purchase-overlap count
  kind: conditional_count
  value_type: count
  variants:
  - first_channel_only
  - second_channel_only
  - both_channels
- id: cumulative_sales_price
  label: Cumulative sales-price sum
  kind: cumulative
  expression: SUM(sales_price_sum) OVER (PARTITION BY item ORDER BY date ROWS UNBOUNDED PRECEDING)
```

