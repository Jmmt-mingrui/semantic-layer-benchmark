# Database configuration

[English](README.md) | [简体中文](README.zh-CN.md)

Every target uses the same runtime database configuration. DuckDB is the default local engine, but the connection can be replaced without changing canonical questions or metrics.

| Variable | Default | Purpose |
| --- | --- | --- |
| `BENCHMARK_DATABASE_URL` | `duckdb:///./data/tpcds/sf1/tpcds.duckdb` | Driver-specific connection URL or database location |
| `BENCHMARK_DATABASE_CATALOG` | unset | Optional catalog/database namespace |
| `BENCHMARK_DATABASE_SCHEMA` | `main` | Schema containing TPC-DS relations |

Secrets must never be committed. An adapter may replace `driver` and `dialect`, but must preserve the SF1 manifest, logical relation names, canonical metrics, and read-only policy.

PostgreSQL SQL under `benchmark/tpcds/sql/reference/postgres/` remains an attributed result oracle and formula reference; it is not the runtime connection contract. DuckDB translations belong under `benchmark/tpcds/sql/reference/duckdb/` and require result-equivalence validation.

Native semantic models resolve physical namespaces during deployment or adapter rendering. The canonical layer never depends on a catalog or schema name.
