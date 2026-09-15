# TPC-DS-derived SF1 runtime data

[English](README.md) | [简体中文](README.zh-CN.md)

The benchmark uses a local TPC-DS-derived scale-factor-1 dataset. It is not an audited TPC benchmark result, and measurements from this repository must not be presented as official or comparable TPC-DS results.

Generated `.dat` files and the DuckDB database are reproducible local runtime artifacts and are intentionally ignored by Git.

## Prerequisite: obtain the official toolkit

TPC lists TPC-DS Tools v4.0.0 on its [current specifications page](https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp). Its download page requires each user to read and accept the TPC Tools licence, register an email address, and use the link delivered by TPC. The repository and its automation therefore do not download, mirror, or redistribute the toolkit.

After downloading the official archive, follow its build instructions (on the supported Linux layout this is normally `make OS=LINUX` from the tools directory) and retain the resulting `dsdgen` binary. Do not substitute DuckDB's built-in generator, a container image, or a third-party mirror for a publishable run: that would change the generator provenance being measured.

## Recommended: run the complete preparation pipeline

From a clean checkout with `.[test]` installed, one command generates SF1, builds the DuckDB snapshot, freezes all 12 representative Gold identities, verifies them, runs benchmark lint, and runs the test suite:

```bash
python -m scripts.prepare_tpcds_sf1 \
  --dsdgen /path/to/TPC-DS-v4.0.0/tools/dsdgen
```

Use `--overwrite` only when deliberately replacing a previous local snapshot. On success, the command prints the generator, logical dataset, database, and Gold-pack hashes plus table, row, question, and statement counts. Preserve that terminal output with the experiment record.

The toolkit, generated `.dat` files, DuckDB database, and local dataset manifest stay uncommitted. Gold files contain hashes and result metadata only; they never contain result rows.

## Individual stages

### 1. Generate SF1 with the official 4.0.0 toolkit

To run stages separately, start with the checked-in generation wrapper:

```bash
python -m scripts.generate_tpcds_sf1 \
  --dsdgen /path/to/TPC-DS-v4.0.0/tools/dsdgen
```

The wrapper executes the equivalent of:

```text
dsdgen -scale 1 -dir <local-output> -force
```

and records local generation metadata including the binary SHA-256. The generated files remain uncommitted.

### 2. Load and identify the DuckDB snapshot

```bash
python -m scripts.load_tpcds_sf1 \
  --generator-version 4.0.0 \
  --generator-binary /path/to/TPC-DS-v4.0.0/tools/dsdgen
```

The loader creates all 25 physical tables, handles the trailing delimiter in `dsdgen` output, and writes `manifests/duckdb-sf1.json` conforming to [`runner/contracts/dataset-manifest.schema.json`](../../../runner/contracts/dataset-manifest.schema.json). The manifest records the generator version and binary hash, DuckDB version, schema/database hashes, every generated input hash, per-table row counts, and the path-independent logical `dataset_sha256`. That logical identity covers the 24 semantic benchmark tables; `dbgen_version` remains validated generator metadata because its generated row contains the wall-clock time and local command path.

Publication validation re-hashes the schema, database, and generated inputs, verifies the logical snapshot identity, checks the live DuckDB version, and checks every live table row count. A manifest without the `dsdgen` binary hash cannot pass publication preflight.

### 3. Freeze the representative-v1 Gold pack

The representative suite contains q01, q02, q03, q05, q12, q14, q21, q36, q39, q49, q75, and q84. Its immutable instances are stored in `benchmark/tpcds/questions/instances/sf1-representative-v1.jsonl`.

After the local SF1 database exists, run:

```bash
python -m scripts.freeze_representative_sf1
python -m scripts.freeze_representative_sf1 --verify
```

The freeze command executes every pinned DuckDB reference statement against exactly that snapshot. q14 and q39 each contain two required statements but remain one question-level unit for accuracy denominators. Each evaluator-only Gold artifact binds:

- dataset manifest SHA-256, logical dataset identity, and database SHA-256;
- the exact question-instance line hash;
- every reference-SQL path and SHA-256;
- result column definitions, row count, and canonical normalized result SHA-256.

Raw result rows are never written to Gold. Changing the dataset manifest, a selected question instance, a reference SQL file, or a Gold file makes verification fail closed.

The earlier `scripts.freeze_tpcds_sf1` q01-only path is retained for compatibility; representative experiments should use `scripts.freeze_representative_sf1`.
