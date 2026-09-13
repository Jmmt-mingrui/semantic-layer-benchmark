# Offline run reports

[English](README.md) | [简体中文](README.zh-CN.md)

The offline report generator turns finalized benchmark artifacts into deterministic JSON and Markdown summaries. It is deliberately downstream of the benchmark boundary: it imports no engine adapter, opens no database, executes no SQL, and reads no evaluator-only Gold asset.

## Accepted inputs

The generator accepts exactly one finalized `run.json`, every `trial.json` referenced by that run, and the `trace.jsonl` next to each trial. Before any output is written, it:

- validates all records with the repository's JSON Schema Draft 2020-12 contracts and format checks;
- confines trial references to the run's `trials/` directory and rejects symlink or path traversal escapes;
- verifies run, experiment, and trial identities, unique trial references and IDs, contiguous trace sequences, lifecycle endpoints, and parent ordering;
- verifies that the run summary agrees with the loaded trial statuses.

The generator does not dereference conversation, SQL, candidate-result, native request/response, error, or answer artifacts. Those references may remain unavailable to the reporting environment.

## Output

`report.json` and `report.md` contain:

- outcome counts for passed, failed, unsupported, invalid, timeout, and skipped trials;
- accuracy over evaluable trials only (`passed / (passed + failed)`);
- evaluator error-category counts;
- provider-token coverage and known totals without converting unknown values to zero;
- tool, database, and native-service call coverage and known totals;
- trial and trace-event latency distributions;
- native-operation counts, statuses, and latency distributions;
- validation counts and the run's reproducibility envelope.

P50 is the median. P95 uses nearest-rank. The report does not rank targets or claim statistical significance; cross-target aggregation and confidence intervals belong to a later analysis layer.

## Usage

Run from the repository root:

```bash
python -m scripts.generate_run_report \
  --artifact-root . \
  --run runs/<run-id>/run.json \
  --output-dir reports/generated/<run-id>
```

English Markdown is the default. Use `--language zh-CN` for a Chinese Markdown report. Existing outputs are protected; pass `--overwrite` only when replacement is intentional.

This command is valid only for finalized protocol or benchmark runs whose records conform to the current `0.1.0` contracts. It fails closed and writes nothing when any input is invalid.
