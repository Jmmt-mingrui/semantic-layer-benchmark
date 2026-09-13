# 原生 Adapter 边界

[English](README.md) | [简体中文](README.zh-CN.md)

原生目标通过封闭且目标特定的 Adapter 边界接入。Benchmark 不定义通用语义查询 API；原生能力不可用时，绝不允许静默替换为直接 SQL。

## 冻结 Gold 的 Runner 接入

`FrozenGoldEvaluator` 是 evaluator-only 组件。Runner 在打开数据库、创建 Provider 或写入任何 run artifact 之前，会校验所有选中题目的精确 Gold 映射：数据集 manifest、快照身份、question-instance、reference SQL 身份、scale factor、结果契约与归一化版本。

目标不会获得 Gold 路径、参考 SQL、结果行或期望 hash。它必须提交且只提交一个 result handle；Runner 只将列、行数和 `canonical-json-v1` hash 交给 evaluator。缺少或多个 handle 归为 `incomplete_result`；身份不匹配归为 `wrong_result`。Runner 不会执行参考 SQL 来生成 fallback 答案。

持久化 conversation 会脱敏 preview rows。Evaluator 耗时作为 telemetry 记录，并从 `usage.scored_latency_ms` 中排除。
