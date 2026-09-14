# Native adapter boundary

[English](README.md) | [简体中文](README.zh-CN.md)

Native targets use a closed, target-specific adapter boundary. The benchmark
does not define a universal semantic query API and must never substitute direct
SQL when a native capability is unavailable.

## Frozen Gold runner integration

`FrozenGoldEvaluator` is evaluator-only code. Before a runner opens the
database, creates a provider, or writes a run artifact, it validates the exact
Gold map for every selected question: dataset manifest, snapshot identity,
question-instance, reference-SQL identity, scale factor, result contract, and
normalization revision.

The target never receives a Gold path, reference SQL, result rows, or expected
hash. It submits exactly one result handle; the runner passes only its columns,
row count, and `canonical-json-v1` hash to the evaluator. Missing or multiple
handles are `incomplete_result`; a non-matching identity is `wrong_result`.
No runner path executes reference SQL to derive a fallback answer.

Persisted conversations redact preview rows. Evaluation duration is recorded as
evaluator telemetry and excluded from `usage.scored_latency_ms`.
