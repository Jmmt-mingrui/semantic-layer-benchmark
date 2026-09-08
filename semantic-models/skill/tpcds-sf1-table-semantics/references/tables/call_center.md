# Call Center

Versioned operating and geographic attributes for catalog call centers.

## Semantic contract

- **Physical table:** `public.call_center`
- **Kind:** dimension
- **Domain:** catalog
- **Grain:** One slowly changing dimension row per call-center version.
- **Primary key:** `cc_call_center_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `cc_call_center_sk` | `integer` | primary key | Surrogate key component identifying the call center row. |
| `cc_call_center_id` | `char(16)` | business identifier | Business identifier for call center. |
| `cc_rec_start_date` | `date` | date attribute | Date on which this dimension version became effective. Nullable. |
| `cc_rec_end_date` | `date` | date attribute | Date on which this dimension version stopped being effective. Nullable. |
| `cc_closed_date_sk` | `integer` | foreign key | Surrogate key to Date; call-center closing date. Nullable. |
| `cc_open_date_sk` | `integer` | foreign key | Surrogate key to Date; call-center opening date. Nullable. |
| `cc_name` | `varchar(50)` | attribute | Name. Nullable. |
| `cc_class` | `varchar(50)` | attribute | Class. Nullable. |
| `cc_employees` | `integer` | attribute | Employees. Nullable. |
| `cc_sq_ft` | `integer` | attribute | Square feet. Nullable. |
| `cc_hours` | `char(20)` | attribute | Hours. Nullable. |
| `cc_manager` | `varchar(40)` | attribute | Manager. Nullable. |
| `cc_mkt_id` | `integer` | business identifier | Business identifier for market. Nullable. |
| `cc_mkt_class` | `char(50)` | attribute | Market class. Nullable. |
| `cc_mkt_desc` | `varchar(100)` | attribute | Market description. Nullable. |
| `cc_market_manager` | `varchar(40)` | attribute | Market manager. Nullable. |
| `cc_division` | `integer` | attribute | Division. Nullable. |
| `cc_division_name` | `varchar(50)` | attribute | Division name. Nullable. |
| `cc_company` | `integer` | attribute | Company. Nullable. |
| `cc_company_name` | `char(50)` | attribute | Company name. Nullable. |
| `cc_street_number` | `char(10)` | business identifier | Street number. Nullable. |
| `cc_street_name` | `varchar(60)` | attribute | Street name. Nullable. |
| `cc_street_type` | `char(15)` | attribute | Street type. Nullable. |
| `cc_suite_number` | `char(10)` | business identifier | Suite number. Nullable. |
| `cc_city` | `varchar(60)` | attribute | City. Nullable. |
| `cc_county` | `varchar(30)` | attribute | County. Nullable. |
| `cc_state` | `char(2)` | attribute | State. Nullable. |
| `cc_zip` | `char(10)` | attribute | Zip. Nullable. |
| `cc_country` | `varchar(20)` | attribute | Country. Nullable. |
| `cc_gmt_offset` | `decimal(5,2)` | attribute | Offset from Greenwich Mean Time in hours. Nullable. |
| `cc_tax_percentage` | `decimal(5,2)` | attribute | Tax percentage. Nullable. |

## Relationships

| Local columns | Target | Cardinality | Meaning |
| --- | --- | --- | --- |
| `cc_closed_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Call-center closing date. |
| `cc_open_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | Call-center opening date. |

## Query guidance

- Join catalog facts with the surrogate key, not the business ID.
- Open, close, and record-effective dates have different meanings.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
