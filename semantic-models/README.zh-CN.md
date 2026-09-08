# 语义模型

[English](README.md) | [简体中文](README.zh-CN.md)

本目录存放统一语义契约，以及各个被测系统的原生表示。所有系统必须描述相同的 PostgreSQL SF1 表结构和业务意图；模型差异应来自格式能力，而不是输入口径不同。

## 当前状态

| 表示方式 | 位置 | 状态 | 用途 |
| --- | --- | --- | --- |
| Skill | [`skill/tpcds-sf1-table-semantics/`](skill/tpcds-sf1-table-semantics/) | 已实现表语义 | Agent 指令及按需加载的表参考文档 |
| OKF v0.2 | [`okf/tpcds-sf1/`](okf/tpcds-sf1/) | 已实现表语义 | 带 YAML 元数据的可移植 Markdown 知识包 |
| Canonical | [`canonical/`](canonical/) | 计划中 | 与具体系统无关的语义和指标契约 |
| MetricFlow | [`metricflow/`](metricflow/) | 计划中 | MetricFlow 原生语义模型 |
| Cube | [`cube/`](cube/) | 计划中 | Cube 原生数据模型 |
| Ossie | [`ossie/`](ossie/) | 计划中 | Ossie 原生语义表示 |
| DDL-only | [`ddl-only/`](ddl-only/) | 计划中 | 不包含增强语义的对照基线 |

Skill 和 OKF 当前覆盖相同的 24 张业务表、425 个物理字段和 106 条显式关系。`dbgen_version` 只记录数据生成器元数据，不属于零售业务表，因此被排除。

## 统一表级契约

每张已实现的表定义都包含：

- 物理表名、业务描述、业务域、表类型、粒度和主键；
- 每个 PostgreSQL 字段的类型、语义角色、含义及可空性；
- 带角色的 Join 和基数，包括销售、发货和退货日期；
- 相互独立的账单、收货、退款和退货客户角色；
- 门店、目录和网站渠道中销售明细与退货明细的复合键关系；
- 可加、不可加和半可加度量的使用规则。

两种表示对同一契约采用不同编码方式。Skill 把行为约束放在 `SKILL.md` 中，并把详细表定义放到 `references/` 下按需加载。OKF 使用 v0.2 知识包，每张表由 YAML frontmatter 和 Markdown 正文组成。本项目把 OKF 作为知识表示来评测，不预设它是可以直接生成 SQL 的语义引擎。

## 来源链

定义来自以下固定来源：

1. **逻辑模型与基准术语：** [TPC-DS v4.0.0 官方规范](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf)。
2. **PostgreSQL 物理表、字段、类型、可空性和主键：** [固定在 commit `63ee712` 的 PostgreSQL DDL](https://github.com/litkhai/tpcds-scripts/blob/63ee7120a89ba5d1c5d8287f98c8e8c427768c98/engines/postgres/ddl/schema.sql)。
3. **OKF 打包规则：** [Open Knowledge Format v0.2 规范](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)。

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

当前版本只定义**表语义**，尚未包含统一指标清单、指标公式、问题与指标映射、各系统的指标语法或可执行适配器。下一阶段应先从 99 个问题中整理统一指标契约，再生成各系统的指标定义。

