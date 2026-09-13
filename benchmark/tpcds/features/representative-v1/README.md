# TPC-DS representative semantic suite v1

[English](README.md) | [简体中文](README.zh-CN.md)

[`selection.json`](selection.json) defines a deliberately small, reviewable 12-question subset of canonical TPC-DS-derived q01–q99. It is the initial **semantic-coverage suite**, not an official TPC-DS selection and not a source of benchmark scores.

## What it covers

The selection covers aggregation, time logic, relational joins, nested queries, cross-fact composition, inventory semi-additivity, analytic windows, derived metrics, entity-detail retrieval, and multiple SQL formulations. It is intentionally evidence-linked: every chosen row repeats the canonical template, statement cardinality, and mapped SQL paths.

| Questions | Role |
|---|---|
| q01, q03, q84 | qualification baseline, grouped aggregation, entity detail |
| q02, q05, q49, q75 | cross-channel / cross-fact and derived measures |
| q12, q36 | windowed revenue share and margin hierarchy |
| q21 | semi-additive inventory snapshot semantics |
| q14, q39 | multiple equivalent reference formulations |

## Boundaries

Selection metadata must not be exposed to a blank-context target as reference SQL context. It supplies no parameters, no materialized question instances, no Gold result, no result rows, no scores, and no engine-specific semantics. A selected question becomes runnable only after its own reviewed instance, frozen Gold identity, and target policy have been declared.

Canonical q01–q99 records are unchanged. Labels are a manual benchmark review, not an official TPC taxonomy. When source files change, update the selection through review rather than silently retaining it.

## Validation

```bash
PYTHONPATH=. pytest -q tests/unit/test_representative_suite.py
```

The test verifies exact selection size, unique canonical IDs, source mapping identity, multi-formulation cardinality, declared capability coverage, and the English-default / Chinese companion documentation convention.
