# Store

Versioned store operations, organization, market, geography, address, time-zone, and tax attributes.

## Semantic contract

- **Physical table:** `public.store`
- **Kind:** dimension
- **Domain:** store
- **Grain:** One slowly changing dimension row per store version.
- **Primary key:** `s_store_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `s_store_sk` | `integer` | primary key | Surrogate key component identifying the store row. |
| `s_store_id` | `char(16)` | business identifier | Business identifier for store. |
| `s_rec_start_date` | `date` | date attribute | Date on which this dimension version became effective. Nullable. |
| `s_rec_end_date` | `date` | date attribute | Date on which this dimension version stopped being effective. Nullable. |
| `s_closed_date_sk` | `integer` | foreign key | Surrogate key to Date; store closing date. Nullable. |
| `s_store_name` | `varchar(50)` | attribute | Store name. Nullable. |
| `s_number_employees` | `integer` | attribute | Number employees. Nullable. |
| `s_floor_space` | `integer` | attribute | Floor space. Nullable. |
| `s_hours` | `char(20)` | attribute | Hours. Nullable. |
| `s_manager` | `varchar(40)` | attribute | Manager. Nullable. |
| `s_market_id` | `integer` | business identifier | Business identifier for market. Nullable. |
| `s_geography_class` | `varchar(100)` | attribute | Geography class. Nullable. |
| `s_market_desc` | `varchar(100)` | attribute | Market description. Nullable. |
| `s_market_manager` | `varchar(40)` | attribute | Market manager. Nullable. |
| `s_division_id` | `integer` | business identifier | Business identifier for division. Nullable. |
| `s_division_name` | `varchar(50)` | attribute | Division name. Nullable. |
| `s_company_id` | `integer` | business identifier | Business identifier for company. Nullable. |
| `s_company_name` | `varchar(50)` | attribute | Company name. Nullable. |
| `s_street_number` | `varchar(10)` | business identifier | Street number. Nullable. |
| `s_street_name` | `varchar(60)` | attribute | Street name. Nullable. |
| `s_street_type` | `char(15)` | attribute | Street type. Nullable. |
| `s_suite_number` | `char(10)` | business identifier | Suite number. Nullable. |
| `s_city` | `varchar(60)` | attribute | City. Nullable. |
| `s_county` | `varchar(30)` | attribute | County. Nullable. |
| `s_state` | `char(2)` | attribute | State. Nullable. |
| `s_zip` | `char(10)` | attribute | Zip. Nullable. |
| `s_country` | `varchar(20)` | attribute | Country. Nullable. |
| `s_gmt_offset` | `decimal(5,2)` | attribute | Offset from Greenwich Mean Time in hours. Nullable. |
| `s_tax_precentage` | `decimal(5,2)` | attribute | Tax precentage. Nullable. |

## Relationships

| Local columns | Target | Cardinality | Meaning |
| --- | --- | --- | --- |
| `s_closed_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Store closing date. |

## Query guidance

- Join store facts with s_store_sk to retain the historical store version.
- The source column s_tax_precentage intentionally preserves the schema spelling.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
