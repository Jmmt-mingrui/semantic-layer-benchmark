# Inventory

Daily on-hand inventory snapshots by item and warehouse.

## Semantic contract

- **Physical table:** `public.inventory`
- **Kind:** fact
- **Domain:** inventory
- **Grain:** One snapshot row per date, item, and warehouse.
- **Primary key:** `inv_date_sk`, `inv_item_sk`, `inv_warehouse_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `inv_date_sk` | `integer` | primary key | Surrogate key to Date; inventory snapshot date. |
| `inv_item_sk` | `integer` | primary key | Surrogate key to Item; stocked item. |
| `inv_warehouse_sk` | `integer` | primary key | Surrogate key to Warehouse; stocking warehouse. |
| `inv_quantity_on_hand` | `integer` | semi-additive measure | Units available in this inventory snapshot. Nullable. |

## Relationships

| Local columns | Target | Cardinality | Meaning |
| --- | --- | --- | --- |
| `inv_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Inventory snapshot date. |
| `inv_item_sk` | [item](item.md).`i_item_sk` | many-to-one | Stocked item. |
| `inv_warehouse_sk` | [warehouse](warehouse.md).`w_warehouse_sk` | many-to-one | Stocking warehouse. |

## Query guidance

- Quantity on hand is semi-additive: sum across items or warehouses at one date, but not across dates.
- Use the snapshot date when comparing inventory before and after an event.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
