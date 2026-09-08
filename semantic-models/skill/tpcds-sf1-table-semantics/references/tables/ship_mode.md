# Ship Mode

Shipping type, code, carrier, and contract attributes for catalog and web fulfillment.

## Semantic contract

- **Physical table:** `public.ship_mode`
- **Kind:** dimension
- **Domain:** shared
- **Grain:** One row per shipping-mode surrogate key.
- **Primary key:** `sm_ship_mode_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `sm_ship_mode_sk` | `integer` | primary key | Surrogate key component identifying the ship mode row. |
| `sm_ship_mode_id` | `char(16)` | business identifier | Business identifier for ship mode. |
| `sm_type` | `char(30)` | attribute | Type. Nullable. |
| `sm_code` | `char(10)` | attribute | Code. Nullable. |
| `sm_carrier` | `char(20)` | attribute | Carrier. Nullable. |
| `sm_contract` | `char(20)` | attribute | Contract. Nullable. |

## Relationships

No outbound semantic joins are defined for this table.

## Query guidance

- Store sales do not use shipping mode.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
