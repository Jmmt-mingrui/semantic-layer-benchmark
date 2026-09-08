# Canonical TPC-DS questions

`questions.jsonl` contains one benchmark task for each of the 99 TPC-DS query templates.

The questions are original, concise paraphrases derived from the functional intent of the TPC-DS v4.0.0 templates. They are not copies of the specification's Business Questions. Template inputs remain symbolic so one question definition can be materialized with qualification values or generated values later.

Each JSONL record contains:

- `id`: stable benchmark identifier (`q01` through `q99`)
- `source_template`: corresponding TPC-DS template
- `question`: canonical English question
- `parameters`: symbolic inputs required to materialize the task
- `multi_statement`: `true` for templates 14, 23, 24, and 39, which contain two related SQL statements

Source: [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), Appendix B. The SQL templates distributed with the official TPC-DS tools remain the functional source of truth when wording and SQL behavior differ.

