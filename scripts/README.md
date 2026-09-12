# Benchmark maintenance commands

[English](README.md) | [简体中文](README.zh-CN.md)

Repository maintenance commands are Python modules so they work consistently from a clean checkout. Run them from the repository root after installing `.[test]`.

## Benchmark lint

```bash
python -m scripts.benchmark_lint
```

The command composes the existing serialized-asset, canonical-question, and native-target checks with repository-wide benchmark invariants:

- canonical q01–q99 definitions and reference SQL remain complete;
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
