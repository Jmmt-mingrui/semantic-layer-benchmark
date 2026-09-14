# TPC-DS 代表性语义题集 v1

[English](README.md) | [简体中文](README.zh-CN.md)

[`selection.json`](selection.json) 定义了一个小而可审查的 12 题子集，来源为 canonical TPC-DS-derived q01–q99。它是初始的**语义能力覆盖题集**，不是官方 TPC-DS 选题，也不是 benchmark 成绩来源。

## 覆盖范围

该题集覆盖聚合、时间逻辑、关系连接、嵌套查询、跨事实表组合、库存半可加性、分析窗口、派生指标、实体明细检索和多种 SQL 表述。每一题都重复 canonical 的模板、语句数量和映射 SQL 路径，因此其证据链可审查。

| 题目 | 作用 |
|---|---|
| q01、q03、q84 | qualification 基线、分组聚合、实体明细 |
| q02、q05、q49、q75 | 跨渠道/跨事实表及派生指标 |
| q12、q36 | 窗口化收入占比和毛利率层级 |
| q21 | 半可加库存快照语义 |
| q14、q39 | 多个等价参考 SQL 表述 |

## 边界

空白上下文 target 不得将选题元数据当作 reference SQL 上下文。它不提供参数、实体化题目实例、Gold 结果、结果行、成绩或任何引擎特有语义。选中的题目只有在声明各自经过审查的 instance、冻结的 Gold identity 和 target policy 后才可执行。

canonical q01–q99 不会被修改。标签来自人工 benchmark review，并非官方 TPC 分类。如果来源文件变化，必须通过 review 更新选题，不能静默沿用。

## 验证

```bash
PYTHONPATH=. pytest -q tests/unit/test_representative_suite.py
```

测试验证精确题数、canonical ID 不重复、source mapping 身份、多表述语句数量、声明能力覆盖，以及英文默认/中文配套文档约定。
