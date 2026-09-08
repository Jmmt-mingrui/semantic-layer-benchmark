# Canonical TPC-DS questions

`questions.jsonl` contains one benchmark task for each of the 99 TPC-DS query templates and records how to trace the question back to its specification section and reviewable SQL.

The questions are original, concise paraphrases derived from the functional intent of the TPC-DS v4.0.0 templates. They are not copies of the specification's Business Questions. Template inputs remain symbolic so one question definition can be materialized with qualification values or generated values later.

Each JSONL record contains:

- `id`: stable benchmark identifier (`q01` through `q99`)
- `source_template`: corresponding official TPC-DS toolkit template
- `question`: canonical English question
- `parameters`: symbolic inputs required to materialize the task
- `multi_statement`: `true` for templates 14, 23, 24, and 39, which contain two related SQL statements
- `source`: TPC-DS specification version, Appendix B section, specification URL, toolkit URL, and official template path
- `reference_sql`: local PostgreSQL SQL file(s), pinned upstream repository and commit, upstream file URL(s), licence, and adaptation source

## Source layers

1. The business intent and numbering come from the [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), Appendix B.
2. The functional source of truth is the corresponding `query_templates/queryN.tpl` file from the [official TPC-DS toolkit download](https://www.tpc.org/TPC_Documents_Current_Versions/download_programs/tools-download-request5.asp?bm_type=TPC-DS&bm_vers=4.0.0&mode=CURRENT-ONLY). Official templates are not vendored because the toolkit is distributed under the TPC EULA.
3. Reviewable SQL is stored under `../../sql/reference/postgres/`. It is TPC-DS-derived PostgreSQL qualification SQL with fixed substitution values, not the official template text. See that directory's `SOURCE.md` and the header of every SQL file.

When a natural-language question, a business-question description, and SQL disagree, the official toolkit template defines the intended query behavior.

