# Native benchmark runner

[English](README.md) | [简体中文](README.zh-CN.md)

The runner now has one lifecycle for the six current experiment conditions: `blank_context`, `ddl_only`, `metricflow`, `ossie`, `okf`, and `skill`. The lifecycle is shared, but semantic content is not normalized: every condition retains the native operations and context declared in `targets.native.yaml`.

## Isolation and fairness

Every `question × target × repetition` creates a new provider object and a new message list. No provider thread, response chain, message history, tool result, or target adapter is reused across trials. Target code receives only the materialized question and its own native surface; Gold, reference SQL, evaluator rules, and hidden question mappings are not imported by `native_runner.py`.

Blank context can discover the DuckDB catalog and execute read-only SQL. DDL-only receives the physical DDL and read-only SQL. MetricFlow exposes only its pinned CLI discovery/query surface and has no direct-SQL fallback. Ossie exposes validated original YAML plus separately declared read-only SQL. OKF exposes original Markdown/frontmatter/link operations plus separately declared read-only SQL. Skill exposes discovery metadata, activation, progressive reference reads, and separately declared read-only SQL.

Provider, model, temperature, maximum output tokens, seed, turn budget, provider timeout, and tool timeout are experiment inputs. `LiveAgentProvider` is a stateless HTTP boundary for configured Chat-Completions-compatible endpoints. It does not request, collect, or infer hidden reasoning. Missing provider token counters are persisted as `unavailable`, never as zero. Provider retries, tool calls, database calls, errors, and end-to-end latency are recorded.

`ScriptedAgentProvider` exists only for deterministic CI protocol tests and is always marked `ranking_eligible: false`. A real-provider connectivity smoke is opt-in and deliberately non-publishing:

```bash
BENCHMARK_AGENT_PROVIDER=... \
BENCHMARK_AGENT_MODEL=... \
BENCHMARK_AGENT_ENDPOINT=... \
BENCHMARK_AGENT_API_KEY_ENV=MY_PROVIDER_KEY \
python scripts/smoke_live_provider.py
```

The smoke prints hashes and usage metadata only. It is not a benchmark score.

## Publication materialization

`publication_orchestrator.py` is the evaluator-side bridge from a closed native candidate to durable publication artifacts. It refuses scripted providers, missing provider response identities, and any candidate whose provider/runtime was not closed. Only then does it compare ordered candidate result hashes with the frozen representative Gold, assign a harness-owned conversation identity, and write schema-validated `trial.json`, `trace.jsonl`, and `conversation.sanitized.jsonl`. Raw result rows and secrets are never copied.

## Legacy control runner

`run-control` remains available for the earlier q01 Blank/DDL contract tests. New semantic-target work should use `runner/core/native_factory.py`, `runner/core/native_runner.py`, and `runner/core/live_provider.py`. Candidate production remains separate from Gold evaluation: target/provider shutdown occurs before an evaluator is allowed to load Gold.
