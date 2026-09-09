# Apache Ossie TPC-DS SF1 语义

[English](README.md) | [简体中文](README.zh-CN.md)

本目录包含一个厂商中立的 Apache Ossie YAML 文档，用于描述共享的 TPC-DS 派生 SF1 模型。

## 固定版本

- Ossie 文档版本：`0.2.0.dev0`
- Ossie 源码 commit：[`c109cf5`](https://github.com/apache/ossie/tree/c109cf5b0a06970a97599e8f7c2a72859822a3a4)
- Core Metadata Specification：[`spec.md#semantic-model`](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/core-spec/spec.md#semantic-model)
- 机器可读 schema：[`core-spec/ossie-schema.json`](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/core-spec/ossie-schema.json)
- 官方 TPC-DS Ossie 示例：[`examples/tpcds_semantic_model.yaml`](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/examples/tpcds_semantic_model.yaml)
- 物理表结构：[固定 PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql)
- 逻辑语义：[TPC-DS v4.0.0 官方规范](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf)

## 官方对文档结构的解释

[Apache Ossie 官方 README](https://github.com/apache/ossie/blob/main/README.md) 说，Ossie 提供的是一个“single JSON- and YAML-based specification that any tool can read and write”（任何工具都可以读写的统一 JSON/YAML 规范）。这里的 `single` 指统一的语义交换规范，并不是要求每个仓库只能有一个文件。

[Core Metadata Specification](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/core-spec/spec.md) 明确定义了模型层次：

- `semantic_model` 是完整语义模型的顶层容器，包含 datasets、relationships 和 metrics；
- `datasets` 是必需的逻辑 Dataset 集合，其中包括事实表和维表；
- 每个 Dataset 的 `source` 指向底层物理表、视图或查询。

[官方 TPC-DS 示例](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/examples/tpcds_semantic_model.yaml) 采用了同样的结构：一个名为 `tpcds_retail_model` 的顶层模型，下面包含 `store_sales`、`date_dim`、`customer`、`item`、`store` 等多个 Dataset，之后再定义 relationships 和 metrics。

因此，本 benchmark 将一个 YAML 文件作为完整 TPC-DS SF1 语义图的标准 Ossie 输入。这是与官方示例一致的文件组织选择，并不表示 Ossie 只有一张物理表，也不表示 Ossie 禁止拆分源文件。如果后续为了维护性拆分文件，跑 benchmark 前仍需要把它们组装并校验为同一个逻辑 Ossie 模型。

## 覆盖范围

文档定义了全部 24 个业务 Dataset、425 个物理 Field、106 条显式 Relationship 和 64 个可加基础聚合。Relationship 保留所有角色化外键，以及门店、目录和网站渠道中销售明细到退货明细的复合键 Join。

日期代理键是 Integer，但由于 TPC-DS 的 `d_date_sk` 来自所表示日期的 Julian date，因此将这些键标记为时间角色维度。库存数量附带 AI 指令，禁止跨快照日期直接求和。

## 当前边界

[`canonical-metric-coverage.yaml`](canonical-metric-coverage.yaml) 已将完整 canonical 指标清单映射到当前固定版本 Ossie 的 Metric 表达式结构。其中，113 个基础 variant 中有 111 个属于 SQL Metric 候选，25 个派生定义也都可以作为表达式候选；2 个参数化基础定义和全部 9 个 query-exact 公式需要逐题上下文才能执行。

Ossie schema 不区分 simple、ratio、derived 或 cumulative Metric 类型，因此这些区别继续保留在 canonical 清单和覆盖元数据中。覆盖文件是实现验收清单，不属于通过 Ossie schema 校验的交换文档本体。
