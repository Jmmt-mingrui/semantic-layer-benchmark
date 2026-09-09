# Apache Ossie TPC-DS SF1 semantics

[English](README.md) | [简体中文](README.zh-CN.md)

This directory contains one vendor-neutral Apache Ossie YAML document for the shared TPC-DS-derived SF1 model.

## Version pin

- Ossie document version: `0.2.0.dev0`
- Ossie source commit: [`c109cf5`](https://github.com/apache/ossie/tree/c109cf5b0a06970a97599e8f7c2a72859822a3a4)
- Core Metadata Specification: [`spec.md#semantic-model`](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/core-spec/spec.md#semantic-model)
- Machine-readable schema: [`core-spec/ossie-schema.json`](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/core-spec/ossie-schema.json)
- Official TPC-DS Ossie example: [`examples/tpcds_semantic_model.yaml`](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/examples/tpcds_semantic_model.yaml)
- Physical schema: [pinned PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql)
- Logical semantics: [TPC-DS v4.0.0 specification](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf)

## Official interpretation of the document shape

The [Apache Ossie README](https://github.com/apache/ossie/blob/main/README.md) says that Ossie provides a “single JSON- and YAML-based specification that any tool can read and write.” In context, `single` describes one common interchange specification; it is not a repository-level rule that every implementation must contain exactly one file.

The [Core Metadata Specification](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/core-spec/spec.md) defines the model shape explicitly:

- `semantic_model` is “The top-level container that represents a complete semantic model, including datasets, relationships, and metrics.”
- `datasets` is a required collection of logical datasets, including fact and dimension tables.
- Each dataset's `source` points to the underlying physical table/view or query.

The [official TPC-DS example](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/examples/tpcds_semantic_model.yaml) follows this shape: one top-level model named `tpcds_retail_model` contains multiple datasets such as `store_sales`, `date_dim`, `customer`, `item`, and `store`, followed by relationships and metrics.

This benchmark therefore keeps one YAML file as the canonical Ossie artifact for the complete TPC-DS SF1 semantic graph. That is a packaging choice aligned with the official example, not a claim that Ossie contains only one physical table or forbids split source files. If the model is split for maintainability later, the parts must still be assembled and validated as the same logical Ossie model before a benchmark run.

## Coverage

The document defines all 24 business datasets, 425 physical fields, 106 explicit relationships, and additive base aggregations. Relationship objects preserve every role-playing foreign key and the composite store, catalog, and web sale-to-return line joins.

Integer date surrogate keys are marked as time-role dimensions because TPC-DS derives `d_date_sk` from the represented Julian date. Inventory quantity includes an AI instruction that prevents aggregation across snapshot dates.

## Current boundary

[`canonical-metric-coverage.yaml`](canonical-metric-coverage.yaml) maps the complete canonical inventory to Ossie's pinned Metric expression shape. It identifies 111 of 113 base variants and all 25 derived definitions as SQL metric candidates. Two parameterized base definitions and all nine query-exact formulas require question context before execution.

Ossie does not declare separate simple, ratio, derived, or cumulative metric types; those distinctions therefore remain in the canonical catalog and coverage metadata. The coverage file is an implementation checklist rather than part of the schema-validated Ossie exchange document.
