# DuckDB reference SQL

This directory will contain DuckDB translations of the attributed PostgreSQL result-oracle queries. Every translation must retain the query ID, source metadata, parameters, and expected semantics, and record each dialect rewrite.

A query is not result-validated until it executes against the pinned SF1 manifest and produces an equivalent normalized result. q01–q10 originally passed DuckDB 1.4.0 empty-schema execution without textual rewrites. The public-output revision adds declared aliases and deterministic presentation tie-breaks; see [`validation.yaml`](validation.yaml) and [`SOURCE.md`](SOURCE.md). All fourteen representative statements have contract checks; this is not a completed SF1 accuracy run.
