# DuckDB reference SQL

This directory will contain DuckDB translations of the attributed PostgreSQL result-oracle queries. Every translation must retain the query ID, source metadata, parameters, and expected semantics, and record each dialect rewrite.

A query is not result-validated until it executes against the pinned SF1 manifest and produces an equivalent normalized result. q01–q10 currently pass DuckDB 1.4.0 empty-schema execution without textual rewrites; see [`validation.yaml`](validation.yaml) and [`SOURCE.md`](SOURCE.md).
