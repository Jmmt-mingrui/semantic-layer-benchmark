# TPC-DS SF1 runtime data

The default local database is `tpcds.duckdb` in this directory. The database file and generated `.dat` inputs are reproducible runtime artifacts and are not committed.

Set `BENCHMARK_DATABASE_URL` to use a different DuckDB file or another supported adapter. Dataset identity comes from the SF1 manifest and checksums, not the engine or file path.

After generating SF1 `.dat` files under `generated/`, build the database with:

```bash
python scripts/load_tpcds_sf1.py
```

The loader creates all 25 physical tables, handles the trailing delimiter in `dsdgen` output, and writes row counts and SHA-256 checksums to `manifests/duckdb-sf1.json`. The 24-table semantic benchmark excludes `dbgen_version`, which remains available as generator metadata.
