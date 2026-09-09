# Apache Ossie TPC-DS SF1 semantics

[English](README.md) | [简体中文](README.zh-CN.md)

This directory contains one vendor-neutral Apache Ossie YAML document for the shared TPC-DS-derived SF1 model.

## Version pin

- Ossie document version: `0.2.0.dev0`
- Ossie source commit: [`c109cf5`](https://github.com/apache/ossie/tree/c109cf5b0a06970a97599e8f7c2a72859822a3a4)
- Machine-readable schema: [`core-spec/ossie-schema.json`](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/core-spec/ossie-schema.json)
- Official TPC-DS Ossie example: [`examples/tpcds_semantic_model.yaml`](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/examples/tpcds_semantic_model.yaml)
- Physical schema: [pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql)
- Logical semantics: [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf)

## Coverage

The document defines all 24 business datasets, 425 physical fields, 106 explicit relationships, and additive base aggregations. Relationship objects preserve every role-playing foreign key and the composite store, catalog, and web sale-to-return line joins.

Integer date surrogate keys are marked as time-role dimensions because TPC-DS derives `d_date_sk` from the represented Julian date. Inventory quantity includes an AI instruction that prevents aggregation across snapshot dates.

## Current boundary

The included aggregate expressions are base semantic inputs, not the final canonical metric inventory. Derived, ratio, cumulative, and question-specific metrics will be added after the 99 questions are normalized into shared definitions.
