# Question-to-metric map

This map covers q01 through q99. `analysis_operations` are query logic, not reusable metrics. An empty metric list means entity retrieval/filtering. SQL-aligned overrides win over an inconsistent paraphrase.

Source of truth: `semantic-models/canonical/tpcds-sf1/question-metric-map.yaml`.

```yaml
questions:
  q01:
    metric_refs:
    - id: return_amount
      variant: store
    analysis_operations:
    - aggregate_by_customer_and_store
    - average_customer_return_by_store
    - greater_than_1_2_times_group_average
  q02:
    metric_refs:
    - id: sales_price_sum
      variant: web
    - id: sales_price_sum
      variant: catalog
    - id: growth_ratio
    analysis_operations:
    - weekday_conditional_aggregation
    - week_sequence_alignment
    - year_over_year_comparison
  q03:
    metric_refs:
    - id: sales_revenue
      variant: store
    analysis_operations:
    - group_by_brand
  q04:
    metric_refs: []
    query_exact_refs:
    - q04_customer_spend_proxy
    analysis_operations:
    - customer_channel_comparison
    - current_vs_prior_year
  q05:
    metric_refs:
    - id: sales_revenue
      variant: store
    - id: sales_revenue
      variant: catalog
    - id: sales_revenue
      variant: web
    - id: net_profit
      variant: store
    - id: net_profit
      variant: catalog
    - id: net_profit
      variant: web
    - id: return_amount
      variant: store
    - id: return_amount
      variant: catalog
    - id: return_amount
      variant: web
    - id: return_net_loss
      variant: store
    - id: return_net_loss
      variant: catalog
    - id: return_net_loss
      variant: web
    analysis_operations:
    - union_channels
    - rollup_channel_and_location
  q06:
    metric_refs:
    - id: customer_count
    analysis_operations:
    - average_item_current_price_by_category
    - price_above_1_2_times_category_average
    - minimum_customer_count
  q07:
    metric_refs:
    - id: average_sales_quantity
      variant: store
    - id: average_list_price
      variant: store
    - id: average_coupon_amount
      variant: store
    - id: average_sales_price
      variant: store
    analysis_operations:
    - promotional_purchase_filter
  q08:
    metric_refs:
    - id: net_profit
      variant: store
    - id: customer_count
    analysis_operations:
    - preferred_customer_threshold
  q09:
    metric_refs:
    - id: sales_row_count
      variant: store
    - id: average_extended_discount_amount
      variant: store
    - id: average_net_paid
      variant: store
    analysis_operations:
    - quantity_bucket
    - threshold_selected_aggregate
  q10:
    metric_refs:
    - id: customer_count
    analysis_operations:
    - store_and_other_channel_intersection
    - group_by_customer_demographics
  q11:
    metric_refs:
    - id: sales_after_discount
      variant: store
    - id: sales_after_discount
      variant: web
    - id: growth_delta
    - id: growth_ratio
    analysis_operations:
    - customer_year_comparison
    - web_growth_greater_than_store_growth
  q12:
    metric_refs:
    - id: sales_revenue
      variant: web
    - id: sales_share_pct
    analysis_operations:
    - class_partition_share
  q13:
    metric_refs:
    - id: average_sales_quantity
      variant: store
    - id: average_extended_sales_price
      variant: store
    - id: average_extended_wholesale_cost
      variant: store
    - id: extended_wholesale_cost
      variant: store
    analysis_operations:
    - demographic_and_price_band_filter
  q14:
    metric_refs:
    - id: list_value_sales
      variant: store
    - id: list_value_sales
      variant: catalog
    - id: list_value_sales
      variant: web
    - id: sales_row_count
      variant: store
    - id: sales_row_count
      variant: catalog
    - id: sales_row_count
      variant: web
    query_exact_refs:
    - q14_average_line_list_value
    analysis_operations:
    - three_channel_item_intersection
    - above_average_filter
    - hierarchy_rollup
    - year_comparison
  q15:
    metric_refs:
    - id: sales_price_sum
      variant: catalog
    analysis_operations:
    - quarter_filter
    - regional_or_large_purchase_filter
  q16:
    metric_refs:
    - id: distinct_order_count
      variant: catalog
    - id: shipping_cost
      variant: catalog
    - id: net_profit
      variant: catalog
    analysis_operations:
    - exclude_returned_orders
    - multiple_warehouse_filter
  q17:
    metric_refs:
    - id: non_null_value_count
    - id: average_sales_quantity
      variant: store
    - id: average_return_quantity
      variant: store
    - id: average_sales_quantity
      variant: catalog
    - id: quantity_stddev
      variant: store_sales
    - id: quantity_stddev
      variant: store_returns
    - id: quantity_stddev
      variant: catalog_sales
    analysis_operations:
    - sold_returned_repurchased_cohort
    - sequential_quarter_windows
  q18:
    metric_refs:
    - id: average_sales_quantity
      variant: catalog
    - id: average_list_price
      variant: catalog
    - id: average_coupon_amount
      variant: catalog
    - id: average_sales_price
      variant: catalog
    - id: average_net_profit
      variant: catalog
    analysis_operations:
    - average_customer_birth_year
    - average_dependent_count
    - county_grouping
  q19:
    metric_refs:
    - id: sales_revenue
      variant: store
    analysis_operations:
    - outside_store_zip_filter
    - revenue_descending
  q20:
    metric_refs:
    - id: sales_revenue
      variant: catalog
    - id: sales_share_pct
    analysis_operations:
    - class_partition_share
  q21:
    metric_refs:
    - id: inventory_quantity_on_hand
      variant: inventory
    - id: inventory_change_pct
    query_exact_refs:
    - q21_inventory_before_after_quantity
    analysis_operations:
    - price_change_date_split
    - warehouse_grouping
  q22:
    metric_refs:
    - id: average_inventory_quantity
    analysis_operations:
    - product_hierarchy_rollup
  q23:
    metric_refs:
    - id: sales_row_count
      variant: store
    - id: gross_sales_value
      variant: store
    - id: list_value_sales
      variant: catalog
    - id: list_value_sales
      variant: web
    analysis_operations:
    - frequent_item_filter
    - top_customer_threshold
    - cross_channel_total
  q24:
    metric_refs:
    - id: net_paid
      variant: store
    analysis_operations:
    - customer_store_grouping
    - compare_to_average_share
    - color_formulations
  q25:
    metric_refs:
    - id: net_profit
      variant: store
    - id: return_net_loss
      variant: store
    - id: net_profit
      variant: catalog
    analysis_operations:
    - sold_returned_repurchased_cohort
  q26:
    metric_refs:
    - id: average_sales_quantity
      variant: catalog
    - id: average_list_price
      variant: catalog
    - id: average_coupon_amount
      variant: catalog
    - id: average_sales_price
      variant: catalog
    analysis_operations:
    - promotional_purchase_filter
  q27:
    metric_refs:
    - id: average_sales_quantity
      variant: store
    - id: average_list_price
      variant: store
    - id: average_sales_price
      variant: store
    - id: average_coupon_amount
      variant: store
    analysis_operations:
    - customer_demographic_filter
  q28:
    metric_refs:
    - id: average_list_price
      variant: store
    - id: non_null_value_count
    - id: distinct_value_count
    analysis_operations:
    - six_parameterized_buckets
  q29:
    metric_refs:
    - id: sales_quantity
      variant: store
    - id: return_quantity
      variant: store
    - id: sales_quantity
      variant: catalog
    analysis_operations:
    - sold_returned_repurchased_cohort
  q30:
    metric_refs:
    - id: return_amount
      variant: web
    analysis_operations:
    - aggregate_by_customer
    - state_average
    - greater_than_1_2_times_state_average
  q31:
    metric_refs:
    - id: sales_revenue
      variant: store
    - id: sales_revenue
      variant: web
    - id: growth_ratio
    analysis_operations:
    - quarter_growth_comparison
    - web_growth_greater_than_store_growth
  q32:
    metric_refs:
    - id: discount_amount
      variant: catalog
    - id: average_extended_discount_amount
      variant: catalog
    analysis_operations:
    - discount_above_1_3_times_period_average
  q33:
    metric_refs:
    - id: sales_revenue
      variant: store
    - id: sales_revenue
      variant: catalog
    - id: sales_revenue
      variant: web
    - id: all_channel_sales_revenue
    analysis_operations:
    - union_channels
    - group_by_manufacturer
  q34:
    metric_refs:
    - id: customer_count
    - id: sales_row_count
      variant: store
    analysis_operations:
    - ticket_item_count_between_15_and_20
    - three_year_month_boundary_cohort
  q35:
    metric_refs:
    - id: customer_count
    analysis_operations:
    - min_max_average_dependent_counts
    - multi_channel_customer_grouping
  q36:
    metric_refs:
    - id: net_profit
      variant: store
    - id: sales_revenue
      variant: store
    - id: gross_margin_ratio
    analysis_operations:
    - rank_within_product_parent
  q37:
    metric_refs:
    - id: inventory_quantity_on_hand
      variant: inventory
    analysis_operations:
    - inventory_range_filter
    - entity_retrieval
  q38:
    metric_refs:
    - id: customer_count
    analysis_operations:
    - three_channel_customer_intersection
  q39:
    metric_refs:
    - id: average_inventory_quantity
    - id: inventory_quantity_stddev
    - id: coefficient_of_variation_pct
    analysis_operations:
    - two_month_comparison
    - coefficient_threshold
  q40:
    metric_refs: []
    query_exact_refs:
    - q40_catalog_net_sales_before_after
    analysis_operations:
    - price_change_date_split
    - warehouse_grouping
  q41:
    metric_refs:
    - id: item_count
    analysis_operations:
    - configured_attribute_combinations
  q42:
    metric_refs:
    - id: sales_revenue
      variant: store
    analysis_operations:
    - group_by_item
  q43:
    metric_refs:
    - id: sales_price_sum
      variant: store
    analysis_operations:
    - weekday_conditional_aggregation
  q44:
    metric_refs:
    - id: average_net_profit
      variant: store
    analysis_operations:
    - best_and_worst_rank
  q45:
    metric_refs:
    - id: sales_price_sum
      variant: web
    analysis_operations:
    - geography_or_item_filter
  q46:
    metric_refs:
    - id: coupon_amount
      variant: store
    - id: net_profit
      variant: store
    analysis_operations:
    - weekend_out_of_town_customer_cohort
  q47:
    metric_refs:
    - id: sales_price_sum
      variant: store
    - id: monthly_average
    - id: deviation_from_average_pct
    - id: growth_delta
    analysis_operations:
    - adjacent_month_comparison
    - rank_within_store_company_brand_category
  q48:
    question_override: Calculate total store quantity sold for configured combinations of customer demographics, sales-price
      ranges, states, and sales-profit ranges.
    metric_refs:
    - id: sales_quantity
      variant: store
    analysis_operations:
    - configured_predicate_combinations
  q49:
    metric_refs:
    - id: sales_quantity
      variant: store
    - id: sales_quantity
      variant: catalog
    - id: sales_quantity
      variant: web
    - id: return_quantity
      variant: store
    - id: return_quantity
      variant: catalog
    - id: return_quantity
      variant: web
    - id: net_paid
      variant: store
    - id: net_paid
      variant: catalog
    - id: net_paid
      variant: web
    - id: return_amount
      variant: store
    - id: return_amount
      variant: catalog
    - id: return_amount
      variant: web
    - id: return_ratio_quantity
      variants:
      - store
      - catalog
      - web
    - id: return_ratio_amount
      variants:
      - store
      - catalog
      - web
    analysis_operations:
    - rank_worst_return_ratio_by_channel
  q50:
    metric_refs:
    - id: elapsed_days_bucket_count
    analysis_operations:
    - store_return_delay_buckets
  q51:
    question_override: For each item and date in a 12-month period, compare cumulative web and store sales-price sums and
      retain dates where web cumulative sales exceed store cumulative sales.
    metric_refs:
    - id: sales_price_sum
      variant: web
    - id: sales_price_sum
      variant: store
    - id: cumulative_sales_price
    analysis_operations:
    - daily_cumulative_window
    - full_outer_join_channel_series
    - web_cumulative_greater_than_store
    source_conflict: Existing question text describes a promotional-share query and does not match query51.sql.
  q52:
    metric_refs:
    - id: sales_revenue
      variant: store
    analysis_operations:
    - group_by_brand
  q53:
    metric_refs:
    - id: sales_price_sum
      variant: store
    - id: monthly_average
    - id: deviation_from_average_pct
    analysis_operations:
    - quarter_and_year_rollup
    - manufacturer_deviation_filter
  q54:
    metric_refs:
    - id: sales_revenue
      variant: store
    - id: customer_count
    analysis_operations:
    - online_or_catalog_then_store_cohort
    - fifty_currency_unit_revenue_bucket
  q55:
    metric_refs:
    - id: sales_revenue
      variant: store
    analysis_operations:
    - group_by_brand
  q56:
    metric_refs:
    - id: sales_revenue
      variant: store
    - id: sales_revenue
      variant: catalog
    - id: sales_revenue
      variant: web
    - id: all_channel_sales_revenue
    analysis_operations:
    - union_channels
    - group_by_item
  q57:
    metric_refs:
    - id: sales_price_sum
      variant: catalog
    - id: monthly_average
    - id: deviation_from_average_pct
    - id: growth_delta
    analysis_operations:
    - adjacent_month_comparison
    - rank_within_call_center_brand_category
  q58:
    metric_refs:
    - id: sales_revenue
      variant: store
    - id: sales_revenue
      variant: catalog
    - id: sales_revenue
      variant: web
    analysis_operations:
    - high_revenue_filter
    - approximately_equal_across_channels
  q59:
    metric_refs:
    - id: sales_price_sum
      variant: store
    - id: growth_ratio
    analysis_operations:
    - weekday_conditional_aggregation
    - weekly_year_over_year_comparison
  q60:
    metric_refs:
    - id: sales_revenue
      variant: store
    - id: sales_revenue
      variant: catalog
    - id: sales_revenue
      variant: web
    - id: all_channel_sales_revenue
    analysis_operations:
    - union_channels
    - group_by_item
  q61:
    metric_refs:
    - id: sales_revenue
      variant: store
    - id: promotion_sales_share_pct
    analysis_operations:
    - promotional_vs_all_sales
  q62:
    metric_refs:
    - id: sales_row_count
      variant: web
    - id: elapsed_days_bucket_count
    analysis_operations:
    - web_shipment_delay_buckets
  q63:
    metric_refs:
    - id: sales_price_sum
      variant: store
    - id: monthly_average
    analysis_operations:
    - manager_month_grouping
  q64:
    metric_refs:
    - id: sales_row_count
      variant: store
    - id: wholesale_cost_sum
      variant: store
    - id: list_price_sum
      variant: store
    - id: coupon_amount
      variant: store
    - id: growth_delta
    query_exact_refs:
    - q64_catalog_sale_to_refund_ratio
    analysis_operations:
    - cross_channel_item_qualification
    - store_year_pair_comparison
  q65:
    metric_refs:
    - id: sales_price_sum
      variant: store
    analysis_operations:
    - average_item_revenue_within_store
    - below_10_percent_of_store_average
  q66:
    question_override: For an eight-hour window in a year, report monthly web and catalog benchmark sales and net values by
      warehouse, including sales per square foot.
    metric_refs:
    - id: sales_per_square_foot
    query_exact_refs:
    - q66_warehouse_monthly_sales_value
    - q66_warehouse_monthly_net_value
    analysis_operations:
    - month_pivot
    - union_web_and_catalog
  q67:
    metric_refs:
    - id: gross_sales_value
      variant: store
    analysis_operations:
    - rank_store_within_category
    - top_rank_filter
  q68:
    metric_refs:
    - id: sales_revenue
      variant: store
    - id: extended_list_price
      variant: store
    - id: extended_tax
      variant: store
    analysis_operations:
    - out_of_town_customer_cohort
  q69:
    metric_refs:
    - id: customer_count
    analysis_operations:
    - store_only_customer_difference
    - group_by_demographics
  q70:
    metric_refs:
    - id: net_profit
      variant: store
    analysis_operations:
    - geography_rollup
    - state_rank
    - top_five_states
  q71:
    metric_refs:
    - id: sales_revenue
      variant: store
    - id: sales_revenue
      variant: catalog
    - id: sales_revenue
      variant: web
    - id: all_channel_sales_revenue
    analysis_operations:
    - breakfast_or_dinner_filter
    - cross_channel_product_ranking
  q72:
    metric_refs:
    - id: sales_row_count
      variant: catalog
    analysis_operations:
    - conditional_count_with_and_without_promotion
    - group_by_item_warehouse_week
  q73:
    metric_refs:
    - id: customer_count
    - id: sales_row_count
      variant: store
    analysis_operations:
    - ticket_item_count_between_1_and_5
    - three_year_first_two_days_cohort
  q74:
    metric_refs:
    - id: net_paid
      variant: store
    - id: net_paid
      variant: web
    - id: growth_ratio
    analysis_operations:
    - customer_year_comparison
    - web_growth_greater_than_store_growth
  q75:
    metric_refs:
    - id: net_sales_quantity
      variants:
      - store
      - catalog
      - web
    - id: net_sales_amount
      variants:
      - store
      - catalog
      - web
    - id: growth_ratio
    - id: growth_delta
    analysis_operations:
    - union_channels_net_of_returns
    - current_vs_previous_year
  q76:
    question_override: For store, web, and catalog sales rows with selected channel-specific foreign keys missing, report
      row count and extended sales amount by channel, missing field, year, quarter, and category.
    metric_refs:
    - id: sales_row_count
      variant: store
    - id: sales_row_count
      variant: web
    - id: sales_row_count
      variant: catalog
    - id: sales_revenue
      variant: store
    - id: sales_revenue
      variant: web
    - id: sales_revenue
      variant: catalog
    analysis_operations:
    - null_key_filter
    - union_channels
    source_conflict: Existing question text describes web promotional averages and does not match query76.sql.
  q77:
    metric_refs:
    - id: sales_revenue
      variant: store
    - id: sales_revenue
      variant: catalog
    - id: sales_revenue
      variant: web
    - id: return_amount
      variant: store
    - id: return_amount
      variant: catalog
    - id: return_amount
      variant: web
    - id: net_profit
      variant: store
    - id: net_profit
      variant: catalog
    - id: net_profit
      variant: web
    - id: return_net_loss
      variant: store
    - id: return_net_loss
      variant: catalog
    - id: return_net_loss
      variant: web
    analysis_operations:
    - union_channels
    - rollup_channel_and_location
  q78:
    question_override: List customer-item pairs whose store-sales quantity is at least twice their combined catalog and web
      quantity, requiring activity in both store and another channel.
    metric_refs:
    - id: sales_quantity
      variant: store
    - id: sales_quantity
      variant: catalog
    - id: sales_quantity
      variant: web
    - id: wholesale_cost_sum
      variant: store
    - id: wholesale_cost_sum
      variant: catalog
    - id: wholesale_cost_sum
      variant: web
    - id: sales_price_sum
      variant: store
    - id: sales_price_sum
      variant: catalog
    - id: sales_price_sum
      variant: web
    analysis_operations:
    - full_outer_join_channel_totals
    - store_quantity_at_least_twice_other_channels
  q79:
    metric_refs:
    - id: coupon_amount
      variant: store
    - id: net_profit
      variant: store
    analysis_operations:
    - monday_large_purchase_customer_cohort
  q80:
    metric_refs:
    - id: sales_revenue
      variant: store
    - id: sales_revenue
      variant: catalog
    - id: sales_revenue
      variant: web
    - id: return_amount
      variant: store
    - id: return_amount
      variant: catalog
    - id: return_amount
      variant: web
    - id: net_profit_after_return_loss
      variants:
      - store
      - catalog
      - web
    analysis_operations:
    - union_channels
    - rollup_channel_location
    - item_price_and_promotion_filter
  q81:
    metric_refs:
    - id: return_amount_including_tax
      variant: catalog
    analysis_operations:
    - aggregate_by_customer
    - state_average
    - greater_than_1_2_times_state_average
  q82:
    metric_refs:
    - id: inventory_quantity_on_hand
      variant: inventory
    analysis_operations:
    - inventory_range_filter
    - entity_retrieval
  q83:
    metric_refs:
    - id: return_quantity
      variant: store
    - id: return_quantity
      variant: catalog
    - id: return_quantity
      variant: web
    analysis_operations:
    - high_return_filter
    - within_10_percent_across_channels
  q84:
    metric_refs: []
    analysis_operations:
    - income_band_range_filter
    - customer_entity_retrieval
  q85:
    question_override: For each web-return reason, calculate average web sales quantity, refunded cash, and return fee across
      configured customer and sales demographic combinations.
    metric_refs: []
    query_exact_refs:
    - q85_average_web_return_values
    analysis_operations:
    - group_by_return_reason
  q86:
    metric_refs:
    - id: sales_price_sum
      variant: web
    analysis_operations:
    - category_class_rollup
    - hierarchy_level
    - rank_within_parent
  q87:
    metric_refs:
    - id: customer_count
    analysis_operations:
    - same_day_three_channel_customer_intersection
  q88:
    metric_refs:
    - id: sales_row_count
      variant: store
    analysis_operations:
    - consecutive_half_hour_buckets
  q89:
    metric_refs:
    - id: sales_price_sum
      variant: store
    - id: monthly_average
    - id: sales_share_pct
    analysis_operations:
    - monthly_share_of_annual_threshold
  q90:
    metric_refs:
    - id: sales_row_count
      variant: web
    - id: time_window_count_ratio
    analysis_operations:
    - morning_vs_evening_count
  q91:
    question_override: For a month and year, report catalog-return net loss by call center and manager for customer groups
      matching gender, education, buy potential, and time zone.
    metric_refs:
    - id: return_net_loss
      variant: catalog
    analysis_operations:
    - group_by_call_center_and_manager
  q92:
    metric_refs:
    - id: discount_amount
      variant: web
    - id: average_extended_discount_amount
      variant: web
    analysis_operations:
    - discount_above_1_3_times_period_average
  q93:
    metric_refs: []
    query_exact_refs:
    - q93_actual_store_sales_after_return
    analysis_operations:
    - return_reason_filter
    - group_by_customer
  q94:
    metric_refs:
    - id: distinct_order_count
      variant: web
    - id: shipping_cost
      variant: web
    - id: net_profit
      variant: web
    analysis_operations:
    - exclude_returned_orders
    - multiple_warehouse_filter
  q95:
    metric_refs:
    - id: distinct_order_count
      variant: web
    - id: shipping_cost
      variant: web
    - id: net_profit
      variant: web
    analysis_operations:
    - require_returned_orders
    - multiple_warehouse_filter
  q96:
    metric_refs:
    - id: sales_row_count
      variant: store
    analysis_operations:
    - half_hour_interval_filter
  q97:
    question_override: Over a 12-month period, count customer-item pairs purchased only in stores, only through catalog, or
      through both channels.
    metric_refs:
    - id: channel_overlap_count
    analysis_operations:
    - full_outer_join_customer_item_sets
    source_conflict: Existing question text describes a promotional adds-to-total ratio and does not match query97.sql.
  q98:
    question_override: For selected categories during the 30 days beginning a start date, report each store-sold item's revenue
      and its percentage of class revenue.
    metric_refs:
    - id: sales_revenue
      variant: store
    - id: sales_share_pct
    analysis_operations:
    - class_partition_share
  q99:
    metric_refs:
    - id: sales_row_count
      variant: catalog
    - id: elapsed_days_bucket_count
    analysis_operations:
    - catalog_shipment_delay_buckets
```

