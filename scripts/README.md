# Benchmark maintenance commands

[English](README.md) | [简体中文](README.zh-CN.md)

Repository maintenance commands are Python modules so they work consistently from a clean checkout. Run them from the repository root after installing `.[test]`.

## Reproduce the SF1 baseline

After personally obtaining and building the official licensed TPC-DS Tools v4.0.0 package, run the complete generation, DuckDB load, representative Gold freeze/verification, lint, and test pipeline:

```bash
python -m scripts.prepare_tpcds_sf1 --dsdgen /path/to/dsdgen
```

The command never downloads the TPC toolkit and never sends data or credentials to an external service. See [`data/tpcds/sf1/README.md`](../data/tpcds/sf1/README.md) for provenance rules and individual stages.

## Benchmark lint

```bash
python -m scripts.benchmark_lint
```

The command composes the existing serialized-asset, canonical-question, and native-target checks with repository-wide benchmark invariants:

- canonical q01–q99 definitions and reference SQL remain complete;
- representative questions expose exact output labels/order, sorting/NULL placement, limits, and multi-output order; parsed outer SQL and bound columns must match those public contracts;
- each English-default `README.md` has a `README.zh-CN.md` counterpart, and vice versa;
- native targets preserve original artifacts, fresh conversations, closed operation sets, and no silent direct-SQL fallback for executable engines;
- no target-visible artifact or tool root overlaps evaluator-only questions or Gold identities;
- generated SF1 data, databases, runtime outputs, traces, reports, and raw result rows are not committed.

Select one or more checks while diagnosing a failure:

```bash
python -m scripts.benchmark_lint --check target-isolation
python -m scripts.benchmark_lint --check readme-pairs --check artifact-hygiene
```

The lint reads Git's tracked-file set when available. Therefore locally generated, correctly ignored SF1 files do not fail a repository-hygiene check; adding them to Git does.

`validate_repository.py` remains the source of the original conformance checks. The lint imports those checks and adds benchmark invariants instead of reimplementing them.

`python -m scripts.materialize_representative_questions` checks the reviewable public definitions against committed JSONL, including identical q01 qualification wording. `--patch` prints a patch without writing files. Changes to question/SQL identities require a new local Gold freeze; they never silently relax result normalization.
