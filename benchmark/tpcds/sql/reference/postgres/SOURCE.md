# PostgreSQL reference SQL: source and status

This directory contains 103 PostgreSQL SQL files representing the 99 TPC-DS query numbers. Queries 14, 23, 24, and 39 each have two formulations, named `_1` and `_2`.

## What these files are

They are fixed-parameter, TPC-DS-derived qualification queries intended to make each canonical question reviewable and executable on PostgreSQL. They are not the official TPC-DS template files, and results produced from this project must be described as **TPC-DS-derived**, not as audited TPC-DS benchmark results.

## Provenance chain

| Layer | Source |
| --- | --- |
| Benchmark definition | [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf), Appendix B |
| Official functional definition | `query_templates/queryN.tpl` in the [TPC-DS v4.0.0 toolkit](https://www.tpc.org/TPC_Documents_Current_Versions/download_programs/tools-download-request5.asp?bm_type=TPC-DS&bm_vers=4.0.0&mode=CURRENT-ONLY), governed by the TPC EULA and not vendored here |
| SQL text upstream | [StarRocks/starrocks](https://github.com/StarRocks/starrocks/tree/9d288306166d2f8ab2ba0294511f977a7da36a1e/fe/fe-core/src/test/resources/sql/tpcds) at `9d288306166d2f8ab2ba0294511f977a7da36a1e`, Apache-2.0 |
| PostgreSQL adaptation | [litkhai/tpcds-scripts](https://github.com/litkhai/tpcds-scripts/tree/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/queries) at `63ee7120a89ba5d1c5d8287f98c8e8c427768c98` |

The PostgreSQL adaptation changes StarRocks-style date arithmetic and expands the `lochierarchy` ORDER BY alias for queries 36, 70, and 86. Every SQL file retains a header with the exact upstream path, pinned commit, licence, and adaptation notice.

## File mapping

- Normal case: canonical `q01` maps to `query01.sql`, through `q99` mapping to `query99.sql`.
- Multi-formulation cases: `q14`, `q23`, `q24`, and `q39` each map to `queryNN_1.sql` and `queryNN_2.sql`.

TPC, TPC-DS, TPC-H, and QphDS are trademarks of the Transaction Processing Performance Council. See the repository `LICENSE` and `THIRD_PARTY_NOTICES.md`.
