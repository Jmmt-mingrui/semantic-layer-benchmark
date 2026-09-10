# TPC-DS SF1 runtime data

[English](README.md) | [简体中文](README.zh-CN.md)

The default local database is `tpcds.duckdb` in this directory. The database file and generated `.dat` inputs are reproducible runtime artifacts and are not committed.

Set `BENCHMARK_DATABASE_URL` to use a different DuckDB file or another supported adapter. Dataset identity comes from the SF1 manifest and checksums, not the engine or file path.

After generating SF1 `.dat` files under `generated/`, build the database with:

```bash
python -m scripts.load_tpcds_sf1 --generator-binary /path/to/dsdgen
```

The loader creates all 25 physical tables, handles the trailing delimiter in `dsdgen` output, and writes a manifest conforming to [`runner/contracts/dataset-manifest.schema.json`](../../../runner/contracts/dataset-manifest.schema.json). It records the generator binary hash, DuckDB version, schema and database hashes, per-table row counts and source hashes, and a path-independent logical `dataset_sha256`. The 24-table semantic benchmark excludes `dbgen_version`, which remains available as generator metadata.

The loader checks that all 25 inputs exist before creating the database and refuses to replace an existing database unless `--overwrite` is supplied. `--generator-binary` may be omitted for local development, but a manifest without its hash cannot pass publication preflight. `--generator-version` defaults to `4.0.0` and must match the official toolkit used to produce the `.dat` files.

After loading, validate all 25 source hashes, the schema and database identities, logical snapshot hash, DuckDB version, and live table row counts; then freeze the evaluator-only q01 result identity:

```bash
python -m scripts.freeze_tpcds_sf1 --require-sources
```

The command writes `benchmark/tpcds/results/gold/sf1/q01.json`. It stores columns, row count, and the normalized result SHA-256, but never result rows. Use `--validate-only` to run the snapshot gates without writing gold. `--development` permits local absolute paths and a missing generator hash, but that output cannot be committed or published.
