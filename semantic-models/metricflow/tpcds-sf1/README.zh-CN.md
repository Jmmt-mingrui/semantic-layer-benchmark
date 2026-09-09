# MetricFlow TPC-DS SF1 语义

[English](README.md) | [简体中文](README.zh-CN.md)

本目录使用 MetricFlow standalone YAML 编写形式：每张 PostgreSQL 物理表对应一个 `semantic_model` 文档，并通过 `node_relation` 直接映射。

## 固定版本

- MetricFlow 源码 commit：[`8750c1d`](https://github.com/dbt-labs/metricflow/tree/8750c1dfe79c9d92e37fc9b8542d544e29f8852e)
- 解析器与 schema：[`metricflow_semantic_interfaces/parsing/schemas.py`](https://github.com/dbt-labs/metricflow/blob/8750c1dfe79c9d92e37fc9b8542d544e29f8852e/metricflow_semantic_interfaces/parsing/schemas.py)
- 物理表结构：[固定 PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql)
- 逻辑语义：[TPC-DS v4.0.0 官方规范](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf)

这里采用开源 MetricFlow 解析器支持的 standalone 格式，不是 dbt Core 1.12 新增的 model-embedded YAML；两种格式不能直接混用，因此必须固定版本。

## 建模决策

- 24 张业务表都直接映射到 `tpcds.public.<table>`。
- 使用 primary、foreign 和 unique Entity 表达简单关系与复合关系。
- 角色化 Join 使用不同 Entity 名称，但复用目标键。
- 保留物理日期键作为 Entity。TPC-DS 日期代理键来自 Julian date，因此使用 PostgreSQL `to_date(..., 'J')` 为事实表提供本地时间维度。
- 可加交易字段使用 `agg: sum`。
- 库存数量通过 `non_additive_dimension` 选择最新快照日期。
- 单价和单位成本只作为 categorical dimension；后续统一指标必须定义合理的平均值或加权公式。
- 每个 Measure 明确设置 `create_metric: false`；显式 Simple Metric 使用 `total_` 前缀，避免与 Measure 同名及重复 proxy metric。

## 当前边界

这些文件定义表语义和可复用 Measure 输入，尚未定义从 99 个问题反向整理出的统一业务指标。
