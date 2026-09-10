# Runner configuration

[English](README.md) | [简体中文](README.zh-CN.md)

Every target uses the same runtime database configuration. DuckDB is the default local engine, but the connection can be replaced without changing canonical questions or metrics.

The directory now contains three distinct inputs:

| File | Purpose |
| --- | --- |
| [`database.yaml`](database.yaml) | Shared read-only database connection contract |
| [`targets.native.yaml`](targets.native.yaml) | Native artifact, operation allowlist, fallback, and readiness definition for every condition |
| [`native-sf1-q01.yaml`](native-sf1-q01.yaml) | Contract pilot selecting one materialized q01 instance and the blank-context baseline |

Experiment and artifact shapes are defined in [`../contracts/`](../contracts/). The exact fresh-conversation behavior is defined in [`../prompts/`](../prompts/).

## Database connection

| Variable | Default | Purpose |
| --- | --- | --- |
| `BENCHMARK_DATABASE_URL` | `duckdb:///./data/tpcds/sf1/tpcds.duckdb` | Driver-specific connection URL or database location |
| `BENCHMARK_DATABASE_CATALOG` | unset | Optional catalog/database namespace |
| `BENCHMARK_DATABASE_SCHEMA` | `main` | Schema containing TPC-DS relations |

Secrets must never be committed. An adapter may replace `driver` and `dialect`, but must preserve the SF1 manifest, logical relation names, canonical metrics, and read-only policy.

PostgreSQL SQL under `benchmark/tpcds/sql/reference/postgres/` remains an attributed result oracle and formula reference; it is not the runtime connection contract. DuckDB translations belong under `benchmark/tpcds/sql/reference/duckdb/` and require result-equivalence validation.

Native semantic models resolve physical namespaces during deployment or adapter rendering. The canonical layer never depends on a catalog or schema name.

Install the runtime and test dependencies with `pip install -e '.[test]'`. `runner.core.database.connect()` currently registers DuckDB and returns normalized columns, rows, and elapsed time; additional drivers can implement the same boundary without changing benchmark inputs.

## Native target policy

The primary harness only intercepts native operations for timeouts, safety, sanitization, and telemetry. It must not convert MetricFlow, Cube, Ossie, OKF, or Skill into shared text before a primary-lane trial. `blank_context` receives database discovery tools but no preloaded schema; `ddl_only` receives DDL and is reported separately.

Readiness is explicit. A target marked `*_pending` cannot be silently skipped or routed through direct SQL. Preflight records it as unavailable until its native model, pinned version, health check, and adapter are present.
