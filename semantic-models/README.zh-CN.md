# 语义模型

[English](README.md) | [简体中文](README.zh-CN.md)

本目录存放统一语义契约，以及各个被测系统的原生表示。所有系统必须描述相同的 PostgreSQL SF1 表结构和业务意图；模型差异应来自格式能力，而不是输入口径不同。

## 当前状态

| 表示方式 | 位置 | 状态 | 用途 |
| --- | --- | --- | --- |
| Skill | [`skill/tpcds-sf1-table-semantics/`](skill/tpcds-sf1-table-semantics/) | 已实现表语义 | Agent 指令及按需加载的表参考文档 |
| OKF v0.2 | [`okf/tpcds-sf1/`](okf/tpcds-sf1/) | 已实现表语义 | 带 YAML 元数据的可移植 Markdown 知识包 |
| Canonical | [`canonical/tpcds-sf1/`](canonical/tpcds-sf1/) | 已抽取候选指标 | 与具体系统无关的指标清单及 q01-q99 映射 |
| MetricFlow | [`metricflow/tpcds-sf1/`](metricflow/tpcds-sf1/) | 已实现表语义 | Standalone MetricFlow YAML 模型和基础 Metric |
| Cube | [`cube/`](cube/) | 计划中 | Cube 原生数据模型 |
| Ossie | [`ossie/tpcds-sf1/`](ossie/tpcds-sf1/) | 已实现表语义 | Apache Ossie `0.2.0.dev0` YAML 交换文档 |
| DDL-only | [`ddl-only/`](ddl-only/) | 计划中 | 不包含增强语义的对照基线 |

Skill、OKF、MetricFlow 和 Ossie 当前描述相同的 24 张业务表和 425 个物理字段。MetricFlow 和 Ossie 还定义了 64 个可加基础聚合；Ossie 将 106 条关系表示成显式对象，MetricFlow 则通过共享 Entity 表达相同的 Join 路径。Canonical SF1 层已经增加 42 个基础指标族、25 个派生指标、9 个 query-exact 公式，以及全部 99 个问题的指标映射。`dbgen_version` 只记录数据生成器元数据，不属于零售业务表，因此被排除。

## 统一表级契约

每张已实现的表定义都包含：

- 物理表名、业务描述、业务域、表类型、粒度和主键；
- 每个 PostgreSQL 字段的类型、语义角色、含义及可空性；
- 带角色的 Join 和基数，包括销售、发货和退货日期；
- 相互独立的账单、收货、退款和退货客户角色；
- 门店、目录和网站渠道中销售明细与退货明细的复合键关系；
- 可加、不可加和半可加度量的使用规则。

各表示对同一契约采用不同编码方式。Skill 把行为约束放在 `SKILL.md` 中，并把详细表定义放到 `references/` 下按需加载。OKF 使用 v0.2 知识包，每张表由 YAML frontmatter 和 Markdown 正文组成。MetricFlow 使用共享 Entity 表示 Join，并通过本地 PostgreSQL 日期表达式提供事实表聚合时间。Ossie 在一个厂商中立文档中表达 Dataset、Field、Relationship 和聚合表达式。按照 Ossie 官方结构，顶层 `semantic_model` 是完整模型容器，下面的 `datasets` 数组才承载逻辑事实表和维表；这里采用一个文件是标准输入的组织选择，不是“只有一张表”。参见 [官方 Core Metadata Specification](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/core-spec/spec.md#semantic-model) 和 [官方 TPC-DS 示例](https://github.com/apache/ossie/blob/c109cf5b0a06970a97599e8f7c2a72859822a3a4/examples/tpcds_semantic_model.yaml)。本项目把 OKF 作为知识表示来评测，不预设它是可以直接生成 SQL 的语义引擎。

## 来源链

定义来自以下固定来源：

1. **逻辑模型与基准术语：** [TPC-DS v4.0.0 官方规范](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf)。
2. **PostgreSQL 物理表、字段、类型、可空性和主键：** [固定在 commit `63ee712` 的 PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql)。
3. **OKF 打包规则：** [Open Knowledge Format v0.2 规范](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)。
4. **MetricFlow 编写与校验：** [固定版本的 MetricFlow 源码](https://github.com/dbt-labs/metricflow/tree/8750c1dfe79c9d92e37fc9b8542d544e29f8852e)。
5. **Ossie 编写与校验：** [固定版本的 Apache Ossie 源码](https://github.com/apache/ossie/tree/c109cf5b0a06970a97599e8f7c2a72859822a3a4)。

本项目属于 TPC-DS 派生工作负载，不是经过审计的正式 TPC 基准实现。仓库不会直接包含 TPC 工具包或生成的 SF1 数据。

## 建模规则

- 聚合之前必须保留物理事实表粒度。
- 使用代理键 Join，不能根据名称相近的描述字段推断关系。
- 即使多个角色指向同一张维表，也必须保持各角色键独立。
- 跨事实表比较前先聚合，防止 Join fanout。
- 在业务口径允许时，可以跨明细行汇总交易数量和扩展金额。
- 单价和单位成本不能直接求和，应使用有明确依据的平均值或加权计算。
- 库存现有量属于半可加度量，不能跨快照日期直接求和。

## 当前边界

当前版本已经定义表语义、基础可加输入和一版**候选统一业务指标清单**。在翻译成各系统原生模型和实现执行适配器之前，仍需审核指标命名、query-exact 公式、问题修正、维度、粒度及 Join 要求。
