# Customer

Customer identity, profile, birth attributes, contact details, and current dimension pointers.

## Semantic contract

- **Physical table:** `public.customer`
- **Kind:** dimension
- **Domain:** shared
- **Grain:** One row per customer surrogate key.
- **Primary key:** `c_customer_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `c_customer_sk` | `integer` | primary key | Surrogate key component identifying the customer row. |
| `c_customer_id` | `char(16)` | business identifier | Business identifier for customer. |
| `c_current_cdemo_sk` | `integer` | foreign key | Surrogate key to Customer Demographics; current customer demographics. Nullable. |
| `c_current_hdemo_sk` | `integer` | foreign key | Surrogate key to Household Demographics; current household demographics. Nullable. |
| `c_current_addr_sk` | `integer` | foreign key | Surrogate key to Customer Address; current customer address. Nullable. |
| `c_first_shipto_date_sk` | `integer` | foreign key | Surrogate key to Date; first ship-to date. Nullable. |
| `c_first_sales_date_sk` | `integer` | foreign key | Surrogate key to Date; first sales date. Nullable. |
| `c_salutation` | `char(10)` | attribute | Salutation. Nullable. |
| `c_first_name` | `char(20)` | attribute | First name. Nullable. |
| `c_last_name` | `char(30)` | attribute | Last name. Nullable. |
| `c_preferred_cust_flag` | `char(1)` | flag | Flag indicating preferred cust. Nullable. |
| `c_birth_day` | `integer` | attribute | Birth day. Nullable. |
| `c_birth_month` | `integer` | attribute | Birth month. Nullable. |
| `c_birth_year` | `integer` | attribute | Birth year. Nullable. |
| `c_birth_country` | `varchar(20)` | attribute | Birth country. Nullable. |
| `c_login` | `char(13)` | attribute | Login. Nullable. |
| `c_email_address` | `char(50)` | attribute | Email address. Nullable. |
| `c_last_review_date` | `char(10)` | date attribute | Last review date. Nullable. |

## Relationships

| Local columns | Target | Cardinality | Meaning |
| --- | --- | --- | --- |
| `c_current_cdemo_sk` | [customer_demographics](customer_demographics.md).`cd_demo_sk` | many-to-one | Current customer demographics. |
| `c_current_hdemo_sk` | [household_demographics](household_demographics.md).`hd_demo_sk` | many-to-one | Current household demographics. |
| `c_current_addr_sk` | [customer_address](customer_address.md).`ca_address_sk` | many-to-one | Current customer address. |
| `c_first_shipto_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | First ship-to date. |
| `c_first_sales_date_sk` | [date_dim](date_dim.md).`d_date_sk` | many-to-one | First sales date. |

## Query guidance

- Facts contain point-in-time demographic and address keys; current customer pointers describe the latest profile only.
- Use the surrogate key for joins and the business ID for display or cross-version identity.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
