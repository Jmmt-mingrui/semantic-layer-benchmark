# Materialized question instances

Files in this directory bridge symbolic canonical questions and agent trials. Qualification records use [`question-instance.schema.json`](../../../../runner/contracts/question-instance.schema.json) v0.1.0; the twelve representative records use [`representative-question-instance.schema.json`](../../../../runner/contracts/representative-question-instance.schema.json) v0.3.0.

The record is split by trust boundary:

- `target_input` contains only the fully rendered question. This is the only compartment the runner may use to build the user message.
- `orchestrator_only` records typed materialization parameters for reproducibility but is never sent to the agent.
- `evaluator_only` contains reference SQL paths, expected statement count, result-comparison behavior, and provenance. It is loaded only after the target sandbox is closed.

q01 qualification is the first reviewed pilot; twelve representative questions are now materialized from the same source chain. The remaining questions still require materialization before a 99-question run. Unresolved `<PLACEHOLDER>` tokens are invalid. q14, q23, q24, and q39 may declare two reference statements; every other question declares one.

Materialized questions must state any output behavior required for result equivalence, including selected fields, grouping, ordering, limits, and whether multiple outputs are expected. This prevents the evaluator from demanding behavior that the agent was never asked to produce.

These files may contain fixed public qualification values, but must never contain expected result rows, result hashes, credentials, or hidden hints.

## Public output contract migration

`public-output-contract-v1` replaces underdefined representative v0.2.0 records with v0.3.0 records and new instance IDs. Parameters use qualification's typed name/type/value array. A single statement has `evaluator_only.result_contract.columns`, `order_sensitive`, `max_rows`, `comparison`, and `order_by`. For q14/q39, `result_contract.statements` contains two such contracts in submission order. `max_rows: null` explicitly means no limit. Comparison remains order-sensitive `exact_normalized` / `canonical-json-v1`; the evaluator adds no column-by-name projection, row sorting, deduplication, or numeric tolerance.

Public requirements are rendered into `target_input.question` at materialization time; the runner still sends only that string. Qualification and representative q01 wording is identical. [Reviewable definitions](../../../../scripts/materialize_representative_questions.py) document the original SQL's date inclusivity, q02 ratio direction/date-pair multiplicity, q49 ascending ranks, q75 detail deduplication, and q84 demographic-key association. Schema/lint bind all fourteen statements' columns and **outer** ORDER BY/LIMIT, and reject requirements present only in hidden metadata.

q02/q14/q39 gain public aliases; q36/q75 gain deterministic final tie-breaks. These are declared presentation changes, not changes to grouping, filters, ratios, ranks, or duplicates. See [SQL revision notes](../../sql/reference/duckdb/SOURCE.md). Old Gold packs and scores cannot be reused with this revision. Re-freeze against the same validated SF1 snapshot; instance/reference hashes reject stale packs. Unit/empty-schema coverage is not a completed live-model SF1 evaluation.

```bash
python -m scripts.materialize_representative_questions
python -m scripts.benchmark_lint --check question-output-contracts
python -m scripts.freeze_representative_sf1
python -m scripts.freeze_representative_sf1 --verify
```

The materializer checks drift by default; `--patch` prints an apply_patch-compatible update without writing files or reading Gold results.
