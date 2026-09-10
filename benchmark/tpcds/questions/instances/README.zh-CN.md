# 实例化问题

本目录是符号化 Canonical Question 与可执行 Agent Trial 之间的桥梁。每条 JSONL 记录都需要符合 [`runner/contracts/question-instance.schema.json`](../../../../runner/contracts/question-instance.schema.json)。

记录按照信任边界分区：

- `target_input` 只包含完全渲染的问题，是 Runner 构建用户消息时唯一可以读取的区域。
- `orchestrator_only` 保存用于复现的强类型实例化参数，但永远不会发送给 Agent。
- `evaluator_only` 包含参考 SQL 路径、预期语句数、结果比较方式和出处，只能在目标 Sandbox 关闭后加载。

q01 Qualification Instance 是第一个经过 Review 的 Pilot。完整运行前，q02–q99 必须根据同一条固定来源链完成实例化。仍包含 `<PLACEHOLDER>` 的问题无效。q14、q23、q24 和 q39 可以声明两条参考语句，其他问题只能声明一条。

实例化问题必须明确写出影响结果一致性的输出要求，包括选择字段、分组、排序、Limit 和是否预期多个输出。这样可以避免 Evaluator 要求 Agent 从未被告知的行为。

这些文件可以包含固定的公开 Qualification 参数，但绝不能包含预期结果行、结果 Hash、凭据或隐藏提示。
