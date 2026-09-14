# DuckDB SQL source and validation

Queries in this directory are derived from the adjacent attributed PostgreSQL references, whose upstream repository, pinned commit, licence, and relationship to the official TPC-DS templates are documented in [`../postgres/SOURCE.md`](../postgres/SOURCE.md).

For q01–q10, DuckDB 1.4.0 required no textual dialect rewrite in the existing empty-schema validation. That check proved parsing, binding, and empty-table execution only; it never established result correctness.

The representative-v1 suite additionally requires q12, q14 (two statements), q21, q36, q39 (two statements), q49, q75, and q84. These source-equivalent candidates are now present under the DuckDB reference directory. **They are not considered frozen or result-equivalent merely because the files exist.** Publication is fail-closed until `scripts/freeze_representative_sf1.py` executes every statement successfully against the same validated TPC-DS-derived SF1 DuckDB snapshot and freezes its normalized result identity.

The local freeze step binds every reference SQL SHA-256 to its question instance, dataset manifest, database snapshot, result columns, row count, and normalized result SHA-256. q14 and q39 keep both required statements inside one question-level Gold artifact so each still contributes one question to execution-accuracy denominators.

No `.dat` file, DuckDB database, or raw result row is committed to this repository.
