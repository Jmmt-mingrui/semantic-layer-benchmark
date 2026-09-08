# Customer Address

Postal, geographic, time-zone, and location-type attributes for customer addresses.

## Semantic contract

- **Physical table:** `public.customer_address`
- **Kind:** dimension
- **Domain:** shared
- **Grain:** One row per customer address surrogate key.
- **Primary key:** `ca_address_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `ca_address_sk` | `integer` | primary key | Surrogate key component identifying the customer address row. |
| `ca_address_id` | `char(16)` | business identifier | Business identifier for address. |
| `ca_street_number` | `char(10)` | business identifier | Street number. Nullable. |
| `ca_street_name` | `varchar(60)` | attribute | Street name. Nullable. |
| `ca_street_type` | `char(15)` | attribute | Street type. Nullable. |
| `ca_suite_number` | `char(10)` | business identifier | Suite number. Nullable. |
| `ca_city` | `varchar(60)` | attribute | City. Nullable. |
| `ca_county` | `varchar(30)` | attribute | County. Nullable. |
| `ca_state` | `char(2)` | attribute | State. Nullable. |
| `ca_zip` | `char(10)` | attribute | Zip. Nullable. |
| `ca_country` | `varchar(20)` | attribute | Country. Nullable. |
| `ca_gmt_offset` | `decimal(5,2)` | attribute | Offset from Greenwich Mean Time in hours. Nullable. |
| `ca_location_type` | `char(20)` | attribute | Location type. Nullable. |

## Relationships

No outbound semantic joins are defined for this table.

## Query guidance

- Billing, shipping, returning, and refunded address roles must remain distinct.
- ZIP codes are strings and may contain extensions or leading zeros.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
