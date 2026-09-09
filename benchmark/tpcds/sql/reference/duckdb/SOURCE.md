# DuckDB SQL source and validation

Queries in this directory are derived from the adjacent attributed PostgreSQL references, whose upstream repository, pinned commit, licence, and relationship to the official TPC-DS templates are documented in [`../postgres/SOURCE.md`](../postgres/SOURCE.md).

For q01–q10, DuckDB 1.4.0 requires no textual dialect rewrite. Each file is copied with an additional DuckDB validation header. On 2026-09-09, all ten files executed successfully against an empty in-memory database created from `data/tpcds/schema/duckdb/schema.sql`.

That check proves parsing, binding, and empty-table execution only. Result equivalence remains pending until the pinned SF1 data manifest is generated and loaded. A query must not be marked result-equivalent based only on this empty-schema check.

