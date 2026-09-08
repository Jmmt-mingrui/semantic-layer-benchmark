# Household Demographics

Household income-band, buying-potential, dependent-count, and vehicle-count combinations.

## Semantic contract

- **Physical table:** `public.household_demographics`
- **Kind:** dimension
- **Domain:** shared
- **Grain:** One row per unique household-demographic combination.
- **Primary key:** `hd_demo_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `hd_demo_sk` | `integer` | primary key | Surrogate key component identifying the household demographics row. |
| `hd_income_band_sk` | `integer` | foreign key | Surrogate key to Income Band; household income band. Nullable. |
| `hd_buy_potential` | `char(15)` | attribute | Buy potential. Nullable. |
| `hd_dep_count` | `integer` | attribute | Dependent count. Nullable. |
| `hd_vehicle_count` | `integer` | attribute | Vehicle count. Nullable. |

## Relationships

| Local columns | Target | Cardinality | Meaning |
| --- | --- | --- | --- |
| `hd_income_band_sk` | [income_band](income_band.md).`ib_income_band_sk` | many-to-one | Household income band. |

## Query guidance

- Join the income band through hd_income_band_sk.
- Fact household keys capture transaction-time context; the customer's current pointer may differ.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
