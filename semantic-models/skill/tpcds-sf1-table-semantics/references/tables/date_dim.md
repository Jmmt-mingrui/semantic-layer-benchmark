# Date

Calendar and fiscal attributes used by all sold, shipped, returned, effective, and access date roles.

## Semantic contract

- **Physical table:** `public.date_dim`
- **Kind:** dimension
- **Domain:** shared
- **Grain:** One row per calendar date.
- **Primary key:** `d_date_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `d_date_sk` | `integer` | primary key | Surrogate key component identifying the date row. |
| `d_date_id` | `char(16)` | business identifier | Business identifier for date. |
| `d_date` | `date` | date attribute | Date. Nullable. |
| `d_month_seq` | `integer` | attribute | Month seq. Nullable. |
| `d_week_seq` | `integer` | attribute | Week seq. Nullable. |
| `d_quarter_seq` | `integer` | attribute | Quarter seq. Nullable. |
| `d_year` | `integer` | attribute | Year. Nullable. |
| `d_dow` | `integer` | attribute | Day of week. Nullable. |
| `d_moy` | `integer` | attribute | Month of year. Nullable. |
| `d_dom` | `integer` | attribute | Day of month. Nullable. |
| `d_qoy` | `integer` | attribute | Quarter of year. Nullable. |
| `d_fy_year` | `integer` | attribute | Fiscal year year. Nullable. |
| `d_fy_quarter_seq` | `integer` | attribute | Fiscal year quarter seq. Nullable. |
| `d_fy_week_seq` | `integer` | attribute | Fiscal year week seq. Nullable. |
| `d_day_name` | `char(9)` | attribute | Day name. Nullable. |
| `d_quarter_name` | `char(6)` | attribute | Quarter name. Nullable. |
| `d_holiday` | `char(1)` | attribute | Holiday. Nullable. |
| `d_weekend` | `char(1)` | attribute | Weekend. Nullable. |
| `d_following_holiday` | `char(1)` | attribute | Following holiday. Nullable. |
| `d_first_dom` | `integer` | attribute | First day of month. Nullable. |
| `d_last_dom` | `integer` | attribute | Last day of month. Nullable. |
| `d_same_day_ly` | `integer` | attribute | Same day ly. Nullable. |
| `d_same_day_lq` | `integer` | attribute | Same day lq. Nullable. |
| `d_current_day` | `char(1)` | flag | Flag indicating current day. Nullable. |
| `d_current_week` | `char(1)` | flag | Flag indicating current week. Nullable. |
| `d_current_month` | `char(1)` | flag | Flag indicating current month. Nullable. |
| `d_current_quarter` | `char(1)` | flag | Flag indicating current quarter. Nullable. |
| `d_current_year` | `char(1)` | flag | Flag indicating current year. Nullable. |

## Relationships

No outbound semantic joins are defined for this table.

## Query guidance

- Every date-key role joins to the same date dimension.
- Filter and group with date attributes after joining the appropriate role-playing key.
- Sequence columns support period-over-period calculations.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
