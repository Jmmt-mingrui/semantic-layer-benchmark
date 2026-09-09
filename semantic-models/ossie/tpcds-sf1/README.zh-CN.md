# Apache Ossie TPC-DS SF1 语义

[English](README.md) | [简体中文](README.zh-CN.md)

本目录包含一个厂商中立的 Apache Ossie YAML 文档，用于描述共享的 TPC-DS 派生 SF1 模型。

## 固定版本

- Ossie 文档版本：`0.2.0.dev0`
- Ossie 源码 commit：[`c109cf5`](https://github.com/apache/ossie/tree/c109cf5b0a06970a97599e8f7c2a72859822a3a4)
- 机器可读 schema：[`core-spec/ossie-schema.json`](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/core-spec/ossie-schema.json)
- 官方 TPC-DS Ossie 示例：[`examples/tpcds_semantic_model.yaml`](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/examples/tpcds_semantic_model.yaml)
- 物理表结构：[固定 PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql)
- 逻辑语义：[TPC-DS v4.0.0 官方规范](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf)

## 覆盖范围

文档定义了全部 24 个业务 Dataset、425 个物理 Field、106 条显式 Relationship 和 64 个可加基础聚合。Relationship 保留所有角色化外键，以及门店、目录和网站渠道中销售明细到退货明细的复合键 Join。

日期代理键是 Integer，但由于 TPC-DS 的 `d_date_sk` 来自所表示日期的 Julian date，因此将这些键标记为时间角色维度。库存数量附带 AI 指令，禁止跨快照日期直接求和。

## 当前边界

当前聚合表达式是基础语义输入，不是最终统一指标清单。Derived、Ratio、Cumulative 和逐题指标将在 99 个问题归一化之后加入。
