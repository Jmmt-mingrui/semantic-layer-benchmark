# 原生 Adapter 边界

[English](README.md) | [简体中文](README.zh-CN.md)

原生语义目标通过 `NativeAdapter` 接入。这是一个刻意保持封闭、目标特定的内部边界：它不定义通用的语义查询 API，也不得静默替换为直接 SQL。

Adapter 只能暴露 `runner/config/targets.native.yaml` 中为该目标声明的操作。目标接收的 `TargetQuestion` 仅由 `target_input.question` 构成；`orchestrator_only`、`evaluator_only`、Gold 结果身份、参考 SQL 和 canonical mapping 都不得跨越这一边界。

每个生产 Adapter 必须：

- 在 trial 前执行目标原生 preflight；
- 暴露原始的原生工具名和请求 payload；
- 记录脱敏后的请求/响应 artifact 与耗时；
- 语义不支持时返回 `unsupported`，不得 fallback；
- 拒绝 evaluator-only 路径、未声明操作，以及该目标注册表禁止的直接 SQL。

Evaluator 是独立组件，也是唯一可以读取 Gold-result identity 的组件。

## 冻结 Gold Evaluator

`FrozenGoldEvaluator` 是 evaluator-only 代码：它不接受 SQL、数据库连接或结果行。它会校验冻结 Gold 与数据集 manifest、question-instance 文件和 reference-SQL 文件的身份，然后只比较候选结果的列、行数、结果 hash，以及固定的 `canonical-json-v1` 归一化版本。

该组件刻意独立于 target adapter。生产 Runner 必须在创建 Provider 前完成加载和校验，并将 evaluator 延迟排除在 target 的 scored latency 之外。
