# Customer Demographics

Reusable combinations of gender, marital status, education, credit, purchase estimate, and dependent counts.

## Semantic contract

- **Physical table:** `public.customer_demographics`
- **Kind:** dimension
- **Domain:** shared
- **Grain:** One row per unique customer-demographic combination.
- **Primary key:** `cd_demo_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `cd_demo_sk` | `integer` | primary key | Surrogate key component identifying the customer demographics row. |
| `cd_gender` | `char(1)` | attribute | Gender. Nullable. |
| `cd_marital_status` | `char(1)` | attribute | Marital status. Nullable. |
| `cd_education_status` | `char(20)` | attribute | Education status. Nullable. |
| `cd_purchase_estimate` | `integer` | attribute | Purchase estimate. Nullable. |
| `cd_credit_rating` | `char(10)` | attribute | Credit rating. Nullable. |
| `cd_dep_count` | `integer` | attribute | Dependent count. Nullable. |
| `cd_dep_employed_count` | `integer` | attribute | Dependent employed count. Nullable. |
| `cd_dep_college_count` | `integer` | attribute | Dependent college count. Nullable. |

## Relationships

No outbound semantic joins are defined for this table.

## Query guidance

- Join through the demographic surrogate key stored on the fact for transaction-time analysis.
- Do not treat demographic combination rows as individual customers.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
