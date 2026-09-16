# DuckDB SQL source and validation

Queries in this directory are derived from the adjacent attributed PostgreSQL references, whose upstream repository, pinned commit, licence, and relationship to the official TPC-DS templates are documented in [`../postgres/SOURCE.md`](../postgres/SOURCE.md).

For q01–q10, DuckDB 1.4.0 required no textual dialect rewrite in the existing empty-schema validation. That check proved parsing, binding, and empty-table execution only; it never established result correctness.

The representative-v1 suite additionally requires q12, q14 (two statements), q21, q36, q39 (two statements), q49, q75, and q84. These source-equivalent candidates are now present under the DuckDB reference directory. **They are not considered frozen or result-equivalent merely because the files exist.** Publication is fail-closed until `scripts/freeze_representative_sf1.py` executes every statement successfully against the same validated TPC-DS-derived SF1 DuckDB snapshot and freezes its normalized result identity.

The local freeze step binds every reference SQL SHA-256 to its question instance, dataset manifest, database snapshot, result columns, row count, and normalized result SHA-256. q14 and q39 keep both required statements inside one question-level Gold artifact so each still contributes one question to execution-accuracy denominators.

No `.dat` file, DuckDB database, or raw result row is committed to this repository.

## Presentation revision: public-output-contract-v1

The original empty-schema check above is historical, not a claim that current files remain byte-identical to their sources.

| Query | Declared presentation change |
| --- | --- |
| q02 | Seven weekday ratio aliases; 2001/2002 direction and calendar-date-pair duplicates unchanged |
| q14 part 1 | `sales` and `number_sales` aggregate aliases |
| q14 part 2 / q84 | ORDER BY uses existing output aliases; values/order unchanged |
| q39 parts 1/2 | Unique month1/month2 aliases, also used in ORDER BY |
| q36 | Category/class tie-breaks after hierarchy/parent/rank; equivalent hierarchy alias in CASE; explicit NULLS LAST |
| q75 | Hierarchy ID tie-breaks after the original difference keys |

Tie-breaks can change rows at a LIMIT boundary or tied-row order: this is a new question/result identity, not a hash-compatible rewrite. Aggregation, filters, ranks, duplicate multiplicity, and upstream provenance are unchanged. Output labels, directions, NULL placement, and limits are public and checked against outer SQL modifiers. `canonical-json-v1` itself is unchanged and still sensitive to column names/order and row order.

Verification covers empty-schema binding/execution and regression fixtures. A real SF1 Gold freeze and live-model rerun are still required locally; old hashes/scores must not be reused. Freeze/verification bind the new instance/SQL hashes and check each result's columns, row cap, and comparison behavior.
