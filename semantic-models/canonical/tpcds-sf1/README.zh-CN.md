# TPC-DS SF1 统一业务指标

[English](README.md) | [简体中文](README.zh-CN.md)

本目录存放第一版与具体系统无关的业务指标契约。指标来自 99 个 canonical questions 及其对应的 103 份 PostgreSQL 参考 SQL。

## 文件

| 文件 | 用途 |
| --- | --- |
| [`metrics.yaml`](metrics.yaml) | 可复用基础指标族、派生指标和 benchmark 特殊公式 |
| [`question-metric-map.yaml`](question-metric-map.yaml) | q01-q99 每个问题对应的指标和分析操作 |

当前候选契约包含 42 个基础指标族、25 个可复用派生指标、9 个 query-exact 指标定义，并且已经覆盖全部 99 个问题。

## 抽取方法

每个问题按照以下优先级解释：

1. 官方 TPC-DS toolkit template 定义查询的预期行为；
2. 仓库中带出处的 PostgreSQL SQL 定义本 benchmark 实际执行的公式；
3. canonical question 提供业务表述和符号化参数。

可复用的数值聚合或比率会成为指标候选。分组字段、过滤条件、Join、排名、集合交集、阈值和 Rollup 记录为 `analysis_operations`，不会自动被当作业务指标。

只有表达相同业务含义时，多个渠道才共用一个指标族。例如，门店、目录和网站渠道的扩展销售金额都属于 `sales_revenue`。`SUM(ss_sales_price)` 则保留为独立的 `sales_price_sum`，因为对单价列求和不等于汇总扩展销售金额。

## 指标层次

- **基础指标族：** 把可复用业务含义绑定到门店、目录、网站、退货或库存的精确表达式；
- **派生指标：** 定义跨渠道合计、占比、增长、利润率、退货率、平均值、离散程度、累计值和条件计数；
- **Query-exact 指标：** 原样保留为保证 SQL 等价性所需的特殊公式，并明确标识，避免下游把它们误当成标准企业 KPI。

## 问题与 SQL 的一致性

抽取过程中发现部分现有问题描述与参考 SQL 明显冲突：

- q51 描述促销占比，但 `query51.sql` 实际比较 Web 与门店累计销售价格；
- q76 描述 Web 促销购买平均值，但 `query76.sql` 实际统计指定外键为空的销售行数和扩展销售金额；
- q97 描述促销比例，但 `query97.sql` 实际统计仅门店、仅目录以及两个渠道共有的 customer-item 组合。

`question-metric-map.yaml` 已为这些冲突记录与 SQL 对齐的 `question_override`，同时精确化 q48、q66、q78、q85、q91 和 q98 的表述。第一版指标提交暂不直接修改 `questions.jsonl`，这样问题修正可以在独立 commit 中审核。

## 在 Benchmark 中的用途

这份候选契约是 MetricFlow、Cube、Ossie、Skill 和 OKF 的统一目标。每种原生实现都需要记录：指标是直接表达、拆成 Measure 加查询逻辑、近似表达，还是不支持。

抽取出指标并不表示每个 TPC-DS 问题只需选择一个指标就能回答。许多问题还需要 Cohort、相关子查询阈值、Full Outer Join、集合交集、Rollup 或窗口函数；这些结构要求已经保留在逐题映射中。

## 当前边界

这是可审核的 v0.1 候选清单，还不是最终 KPI 契约。在翻译到各原生系统之前，下一轮需要：

1. 审核并确认与 SQL 对齐的问题修正；
2. 对照官方 toolkit template 复核 query-exact 公式；
3. 决定哪些特殊表达式只保留为问题局部逻辑，而不升级为可复用指标；
4. 为每个问题映射补齐统一 Dimension、Entity、时间粒度和必需 Join 路径。
