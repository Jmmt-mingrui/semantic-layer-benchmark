# TPC-DS SF1 schema overview

This benchmark models retail activity across store, catalog, and web channels with shared conformed dimensions.

## Global join rules

- Join each fact role to the corresponding dimension surrogate key; never join facts through descriptive attributes.
- Billing and shipping customer/address/demographic keys describe different roles and must not be collapsed.
- Refunded and returning customer roles on catalog and web returns are distinct.
- Date and time dimensions are role-playing: sold, shipped, returned, effective, opened, closed, created, and accessed roles share dimensions but not meanings.
- Direct fact-to-fact joins are limited to the documented composite sale/return line keys. Aggregate facts before broader cross-channel comparisons to avoid fanout.

## Measure behavior

- Additive: quantities and extended transaction/return amounts across line rows.
- Non-additive: unit list price, sales price, and wholesale cost; aggregate with an appropriate average or weighted calculation.
- Semi-additive: inventory quantity on hand; aggregate across item or warehouse at a single snapshot date, not across dates.

## Tables

### Store channel

- [Store](tables/store.md) — Versioned store operations, organization, market, geography, address, time-zone, and tax attributes.
- [Store Returns](tables/store_returns.md) — Returned store line items with customer context, reason, refund disposition, and net loss.
- [Store Sales](tables/store_sales.md) — Point-of-sale line items with customer context, promotion, store, and financial measures.

### Catalog channel

- [Call Center](tables/call_center.md) — Versioned operating and geographic attributes for catalog call centers.
- [Catalog Page](tables/catalog_page.md) — Catalog page, department, catalog number, and active-date attributes.
- [Catalog Returns](tables/catalog_returns.md) — Returned catalog line items, refund roles, return reasons, and financial effects.
- [Catalog Sales](tables/catalog_sales.md) — Catalog order line items with billing, shipping, fulfillment, promotion, and financial measures.

### Web channel

- [Web Page](tables/web_page.md) — Versioned web-page identity, lifecycle, ownership, URL, type, and content-volume attributes.
- [Web Returns](tables/web_returns.md) — Returned web line items, refunded and returning customer roles, reason, and financial effects.
- [Web Sales](tables/web_sales.md) — Web order line items with billing, shipping, site/page, fulfillment, promotion, and financial measures.
- [Web Site](tables/web_site.md) — Versioned website operations, market, organization, address, time-zone, and tax attributes.

### Inventory

- [Inventory](tables/inventory.md) — Daily on-hand inventory snapshots by item and warehouse.

### Shared dimensions

- [Customer](tables/customer.md) — Customer identity, profile, birth attributes, contact details, and current dimension pointers.
- [Customer Address](tables/customer_address.md) — Postal, geographic, time-zone, and location-type attributes for customer addresses.
- [Customer Demographics](tables/customer_demographics.md) — Reusable combinations of gender, marital status, education, credit, purchase estimate, and dependent counts.
- [Date](tables/date_dim.md) — Calendar and fiscal attributes used by all sold, shipped, returned, effective, and access date roles.
- [Household Demographics](tables/household_demographics.md) — Household income-band, buying-potential, dependent-count, and vehicle-count combinations.
- [Income Band](tables/income_band.md) — Lower and upper household-income bounds used by household demographics.
- [Item](tables/item.md) — Versioned product identity, hierarchy, manufacturer, price, physical, and manager attributes.
- [Promotion](tables/promotion.md) — Promotion identity, active dates, cost, target, channels, purpose, and discount state.
- [Return Reason](tables/reason.md) — Standard reason codes and descriptions used by return facts.
- [Ship Mode](tables/ship_mode.md) — Shipping type, code, carrier, and contract attributes for catalog and web fulfillment.
- [Time](tables/time_dim.md) — Time-of-day attributes including hour, minute, second, AM/PM, shift, and meal period.
- [Warehouse](tables/warehouse.md) — Warehouse identity, capacity, address, geography, and time-zone attributes.

## Source

Table and column definitions are based on the [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf) and the benchmark's [pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql).
