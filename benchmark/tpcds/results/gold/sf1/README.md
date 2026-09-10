# Evaluator-only SF1 gold identities

[English](README.md) | [简体中文](README.zh-CN.md)

This directory stores result identities, not result rows. A gold artifact binds one materialized question and reference SQL file to one validated TPC-DS-derived SF1 dataset manifest and records the normalized result SHA-256, columns, and row count.

Targets must never mount or read this directory. The evaluator opens a gold identity only after the target conversation has closed and a final result handle has been submitted.

`q01.json` is intentionally absent until an official TPC-DS v4.0.0 `dsdgen` binary and all 25 generated SF1 inputs pass publication preflight. Generate it with:

```bash
python -m scripts.freeze_tpcds_sf1 --require-sources
```

Development mode exists only for tests and local diagnosis. Its output cannot be committed or reported as a benchmark result.
