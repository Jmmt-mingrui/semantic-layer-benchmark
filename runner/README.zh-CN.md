# 控制组 Runner

[English](README.md) | [简体中文](README.zh-CN.md)

第一条可执行 Harness 覆盖 `blank_context` 和 `ddl_only` 两个控制组。它不会通过共享文本 Adapter 假装实现某个语义目标。

原生语义目标通过内部的[原生 Adapter 边界](core/README.zh-CN.md)接入：目标代码只能收到已实例化的 target question，保留已声明的原生操作，且不得读取 evaluator-only 资产或回退到未声明操作。

## 已强制执行的规则

- 每个 Trial 都创建新的 Provider 实例和全新消息列表；
- 空白上下文初始消息不包含 DDL 或表名；
- 物理 DuckDB DDL 只在 DDL-only 条件中预加载；
- 严格使用 `targets.native.yaml` 中声明的操作 Allowlist；
- 使用 JSON Schema 校验 Tool 输入输出、问题、实验、Trace、Trial 和 Run；
- 执行 DuckDB Parse 检查、只读语句 Allowlist、外部 I/O 禁止规则、语句数和尝试次数预算；
- Agent 不再接收 Turn 后，才执行 Evaluator-only 参考 SQL；
- 记录结果 Hash、q01 精确比较、脱敏 Transcript、Tool Event、Token 字段和延迟字段；
- 校验数据集、数据库文件、配置、Prompt、问题、目标注册表和仓库身份。

数据库和 Trial Deadline 当前采用协作式执行：已经完成但超时的调用会被拒绝，Provider Adapter 必须遵守传给 `AgentProvider.complete` 的 Timeout。对不可信的真实 Provider，仍需使用进程或容器隔离。

## Scripted 协议运行

CLI 提供确定性的 Scripted Provider，使 CI 能验证完整协议，同时不会产生误导性的模型 Benchmark 分数：

```bash
pip install -e '.[test]'
semantic-benchmark run-control \
  --config runner/config/control-sf1-q01.yaml \
  --provider scripted \
  --script /path/to/local-q01-script.json
```

Script 是本地输入，必须为每个计划 Trial 提供 Turn 列表。Key 格式为 `<instance_id>:<target>:r<两位 repetition>`。每个 Turn 可包含 `content`、`response_id`、Provider `usage`，以及带 `id`、`name` 和 `arguments` 的 `tool_calls`。

Scripted Run 只能证明 Orchestration 和 Evaluator 行为，必须标记为协议测试，并排除在公开模型排名之外。下一条集成边界是真实 Provider Adapter；它必须映射 Provider 的原生 Tool-calling 消息，并禁止跨 Trial 复用对话状态。

运行产物写入配置中的 `artifacts.run_directory`。完整结果行只在内存中用于评测；持久化的 Candidate Result Artifact 仅包含列名、行数和 SHA-256。
