# Materialized question instances

Files in this directory are the executable bridge between symbolic canonical questions and agent trials. Each JSONL record conforms to [`runner/contracts/question-instance.schema.json`](../../../../runner/contracts/question-instance.schema.json).

The record is split by trust boundary:

- `target_input` contains only the fully rendered question. This is the only compartment the runner may use to build the user message.
- `orchestrator_only` records typed materialization parameters for reproducibility but is never sent to the agent.
- `evaluator_only` contains reference SQL paths, expected statement count, result-comparison behavior, and provenance. It is loaded only after the target sandbox is closed.

The q01 qualification instance is the first reviewed pilot. q02–q99 must be materialized from the same pinned source chain before a full run. A question with unresolved `<PLACEHOLDER>` tokens is invalid. q14, q23, q24, and q39 may declare two reference statements; every other question declares one.

Materialized questions must state any output behavior required for result equivalence, including selected fields, grouping, ordering, limits, and whether multiple outputs are expected. This prevents the evaluator from demanding behavior that the agent was never asked to produce.

These files may contain fixed public qualification values, but must never contain expected result rows, result hashes, credentials, or hidden hints.
