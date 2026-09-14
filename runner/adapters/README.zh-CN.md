# 原生目标 Adapter

[English](README.md) | [简体中文](README.zh-CN.md)

本目录存放目标特定的 Benchmark Adapter，并非共享的语义 API。每个 Adapter
只能暴露目标已声明的原生操作，保留原生请求形状；不得直接 SQL 或跨目标
fallback，遇到不满足约定的情况必须 fail-closed。

## MetricFlow Adapter

[`metricflow.py`](metricflow.py) 只封装
[`../config/targets.native.yaml`](../config/targets.native.yaml) 固定源码版本
对应的官方 `mf` CLI：

| Benchmark 操作 | 固定的原生命令 |
| --- | --- |
| `metricflow.health_checks` | `mf health-checks` |
| `metricflow.validate_configs` | `mf validate-configs` |
| `metricflow.list_metrics` | `mf list metrics` |
| `metricflow.list_dimensions` | `mf list dimensions --metrics <逗号分隔>` |
| `metricflow.list_dimension_values` | `mf list dimension-values --metrics <…> --dimension <…>` |
| `metricflow.list_entities` | `mf list entities --metrics <逗号分隔>` |
| `metricflow.query` | `mf query --metrics <逗号分隔> …` |

实现固定在 MetricFlow commit
[`8750c1d`](https://github.com/dbt-labs/metricflow/tree/8750c1dfe79c9d92e37fc9b8542d544e29f8852e)，
包版本为 `0.213.0.dev0`。任何请求前，Adapter 都要求 version probe、
source model-layout 检查、`health-checks` 和 `validate-configs` 成功，并在
外部准备好的兼容 dbt runtime project 中执行。仓库里的 standalone model root
会被单独记录，不能当作真实运行时已就绪的证据。

响应记录原生 argv、退出码、stdout/stderr、耗时和确定性的请求/响应 identity。
Adapter 不打开数据库、不生成 SQL、不调用 `db.execute_readonly`，也不暴露
Gold artifact。可识别的缺失语义成员记录为 `unsupported`，其他非零退出记录为
`failed`。单元测试只使用 fake subprocess boundary，不声称 CI 已执行 MetricFlow。

## Apache Ossie 原生 Consumer

[`ossie.py`](ossie.py) 直接读取 Ossie 原生 YAML，不会把模型转换成 Skill、OKF、
normalized chunks 或共享的 `SemanticEvidence`。Benchmark 固定到 Apache Ossie
commit [`c109cf5`](https://github.com/apache/ossie/tree/c109cf5b0a06970a97599e8f7c2a72859822a3a4)，
并固定 `core-spec/ossie-schema.json` 的 blob
`4e50f1eeafd3c56c700e6c5482f9b356b34e1fee`。CI 使用的 schema 副本位于
[`schemas/ossie-c109cf5-schema.json`](schemas/ossie-c109cf5-schema.json)。

Consumer 实现三个 Ossie 操作：

| 操作 | 行为 |
| --- | --- |
| `ossie.validate` | 使用固定的官方 JSON Schema 校验原始 YAML，并校验 Dataset、Field、Relationship、Metric 的本地引用。 |
| `ossie.inspect_model` | 按对象类型和可选原生 ID 发现对象，不返回统一化后的语义内容。 |
| `ossie.read_native_yaml` | 返回完整原始 YAML，或某个 Dataset、Field、Relationship、Metric、semantic model 在原文件中的精确源码片段。 |

对象索引只会在校验成功后建立，而且只记录原始 YAML 中的位置。Field 可以使用
类似 `tpcds_sf1_retail/store_sales/ss_item_sk` 的 fully-qualified native ID；只有
在短 ID 唯一时才允许直接使用短 ID。返回内容直接截取自原始 YAML 文本，不进行
重序列化或跨格式转换。

访问 telemetry 仅记录 operation、对象类型/ID、读取字节数、耗时和 SHA-256；
绝不记录 YAML 内容、SQL、查询结果、Benchmark Gold 或 question-to-metric mapping。
Consumer 会拒绝路径穿越、symlink、evaluator/Gold 路径、未声明操作、共享语义
转换、Embedding 和 Vector Index。

Ossie 不被当成 SQL Runtime。`db.execute_readonly` 仍然是独立的 harness 操作：
SQL 由 Agent 编写，再通过只读 DuckDB 边界执行。Ossie Consumer 自身不会打开
DuckDB，也不会伪造一个不存在的 Ossie query engine。

## Skill Host Adapter

`SkillHostAdapter` 将
`semantic-models/skill/tpcds-sf1-table-semantics` 作为原生 Skill package
挂载。发现阶段只暴露 frontmatter 推导的元数据，以及不可变 package/host
revision identity；不会枚举或读取 `SKILL.md` 和任何 reference。

Agent 必须显式调用 `skill.activate`，Host 才会加载完整 `SKILL.md`。激活后，
`skill.read_reference` 每次仅按需读取一个 UTF-8 且相对 package 的文件。Host
会拒绝路径穿越、绝对路径、package symlink、evaluator/Gold 路径、预加载全部
reference、共享 chunk 转换和未声明 fallback。访问 telemetry 只记录 operation、
脱敏相对路径、字节数、SHA-256 与耗时；绝不记录文档内容、SQL、结果或 Gold 数据。

Skill Adapter 不产生分数。SQL 执行与评估仍是独立且显式声明的 Benchmark 操作。
