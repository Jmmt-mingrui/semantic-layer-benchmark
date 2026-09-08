# Return Reason

Standard reason codes and descriptions used by return facts.

## Semantic contract

- **Physical table:** `public.reason`
- **Kind:** dimension
- **Domain:** shared
- **Grain:** One row per return-reason surrogate key.
- **Primary key:** `r_reason_sk`

## Columns

| Column | PostgreSQL type | Semantic role | Meaning |
| --- | --- | --- | --- |
| `r_reason_sk` | `integer` | primary key | Surrogate key component identifying the return reason row. |
| `r_reason_id` | `char(16)` | business identifier | Business identifier for reason. |
| `r_reason_desc` | `char(100)` | attribute | Reason description. Nullable. |

## Relationships

No outbound semantic joins are defined for this table.

## Query guidance

- Use the reason key from the relevant return channel.

## Sources

- [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), logical schema and column definitions.
- [Pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql) used by this benchmark scaffold.
