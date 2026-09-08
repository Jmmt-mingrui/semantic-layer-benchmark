# Third-party notices

## TPC-DS

TPC-DS is a benchmark specification owned by the [Transaction Processing Performance Council](https://www.tpc.org/). The official specification, query templates, data generator, query generator, and answer sets are distributed under the TPC End User Licensing Agreement and are not relicensed by this repository.

TPC, TPC-DS, TPC-H, and QphDS are trademarks of the Transaction Processing Performance Council. Workloads and measurements in this repository are TPC-DS-derived and are not audited TPC benchmark results.

## StarRocks-derived SQL

The PostgreSQL reference SQL under `benchmark/tpcds/sql/reference/postgres/` is derived from TPC-DS SQL published in the [StarRocks repository](https://github.com/StarRocks/starrocks) at commit `9d288306166d2f8ab2ba0294511f977a7da36a1e` under Apache License 2.0.

Copyright 2021-present StarRocks, Inc. All rights reserved.

The SQL was adapted for PostgreSQL by [litkhai/tpcds-scripts](https://github.com/litkhai/tpcds-scripts) at commit `63ee7120a89ba5d1c5d8287f98c8e8c427768c98`. Each vendored SQL file identifies its precise upstream path and changes. The repository root `LICENSE` contains the Apache License 2.0 text.
