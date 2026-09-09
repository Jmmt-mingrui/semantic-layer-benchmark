# DuckDB reference SQL

This directory will contain DuckDB translations of the attributed PostgreSQL result-oracle queries. Every translation must retain the query ID, source metadata, parameters, and expected semantics, and record each dialect rewrite.

A query is not translated until it executes against the pinned SF1 manifest and produces an equivalent normalized result.

