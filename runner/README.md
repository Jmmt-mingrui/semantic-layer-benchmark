# Control runner

[English](README.md) | [简体中文](README.zh-CN.md)

The first executable harness covers the `blank_context` and `ddl_only` controls. It deliberately does not implement a semantic target through a shared text adapter.

## What is enforced

- a new provider instance and fresh message list for every trial;
- no DDL or table names in the blank-context initial messages;
- physical DuckDB DDL preloaded only for the DDL-only condition;
- the exact operation allowlist from `targets.native.yaml`;
- JSON Schema validation for tool inputs, tool outputs, questions, experiments, traces, trials, and runs;
- DuckDB parse checks, a read-only statement allowlist, external-I/O denial, statement and attempt budgets;
- evaluator-only reference SQL execution after the Agent stops receiving turns;
- result hashing, exact q01 comparison, sanitized transcripts, tool events, token fields, and latency fields;
- dataset, database-file, config, prompt, question, registry, and repository identity checks.

The database and trial deadlines are currently cooperative: a completed call that exceeds its deadline is rejected, and provider adapters must honor the timeout passed to `AgentProvider.complete`. Process/container isolation remains required for untrusted live providers.

## Scripted protocol run

The bundled CLI accepts a deterministic scripted provider so CI can exercise the complete protocol without producing a misleading model benchmark score:

```bash
pip install -e '.[test]'
semantic-benchmark run-control \
  --config runner/config/control-sf1-q01.yaml \
  --provider scripted \
  --script /path/to/local-q01-script.json
```

The script is local input and must contain one turn list for every planned trial. Keys use `<instance_id>:<target>:r<two-digit repetition>`. Each turn may contain `content`, `response_id`, provider `usage`, and `tool_calls` with `id`, `name`, and `arguments`.

Scripted runs prove orchestration and evaluator behavior only. They must be labeled as protocol tests and excluded from published model rankings. A live provider adapter is the next integration boundary; it must translate the provider's native tool-calling messages without reusing conversation state across trials.

Run artifacts are written below the configured `artifacts.run_directory`. Full result rows remain in memory for evaluation; persisted candidate result artifacts contain columns, row count, and SHA-256 only.
