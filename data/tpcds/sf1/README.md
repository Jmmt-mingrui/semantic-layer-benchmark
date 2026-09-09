# TPC-DS SF1 runtime data

The default local database is `tpcds.duckdb` in this directory. The database file and generated `.dat` inputs are reproducible runtime artifacts and are not committed.

Set `BENCHMARK_DATABASE_URL` to use a different DuckDB file or another supported adapter. Dataset identity comes from the SF1 manifest and checksums, not the engine or file path.

