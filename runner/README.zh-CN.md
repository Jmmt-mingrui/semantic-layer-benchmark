# 原生 Benchmark Runner

[English](README.md) | [简体中文](README.zh-CN.md)

当前 Runner 已为六个实验条件提供统一生命周期：`blank_context`、`ddl_only`、`metricflow`、`ossie`、`okf` 和 `skill`。统一的是 Trial 生命周期，不是语义内容；每个条件仍严格保留 `targets.native.yaml` 声明的原生操作与上下文。

## 隔离与公平性

每个 `question × target × repetition` 都创建新的 Provider 对象和新的消息列表。不同 Trial 之间不复用 Provider thread、response chain、消息历史、Tool 结果或 Target Adapter。目标代码只能拿到实例化后的问题及自身原生 Surface；`native_runner.py` 不导入 Gold、参考 SQL、Evaluator 规则或隐藏的 question-to-metric 映射。

Blank 可以发现 DuckDB Catalog 并执行只读 SQL；DDL-only 获得物理 DDL 和只读 SQL；MetricFlow 只暴露固定版本 CLI 的发现与 Query 接口，禁止直接 SQL fallback；Ossie 暴露校验后的原始 YAML，再通过单独声明的只读 SQL 执行；OKF 暴露原始 Markdown、Frontmatter 与链接操作，再通过只读 SQL 执行；Skill 初始只暴露发现元数据，激活后加载指令并按需读取 Reference，再通过只读 SQL 执行。

Provider、模型、Temperature、最大输出 Token、Seed、Turn Budget、Provider Timeout 和 Tool Timeout 都是实验配置输入。`LiveAgentProvider` 是无会话状态的 HTTP Provider 边界，可连接配置注入的 Chat-Completions-compatible Endpoint。它不会请求、采集或推断隐藏推理过程。Provider 未返回 Token 计数时，Trial 中明确记录为 `unavailable`，绝不记为 0。同时记录 Provider Retry、Tool Call、数据库调用、错误和端到端延迟。

`ScriptedAgentProvider` 只用于确定性的 CI 协议测试，始终标记为 `ranking_eligible: false`。真实 Provider 连通性 Smoke Test 为显式启用、非发布型测试：

```bash
BENCHMARK_AGENT_PROVIDER=... \
BENCHMARK_AGENT_MODEL=... \
BENCHMARK_AGENT_ENDPOINT=... \
BENCHMARK_AGENT_API_KEY_ENV=MY_PROVIDER_KEY \
python scripts/smoke_live_provider.py
```

Smoke 只输出 Hash 与 Usage 元数据，不生成 Benchmark 分数。

## 旧控制组 Runner

早期 q01 Blank/DDL 契约测试仍可使用 `run-control`。新的语义目标实验应使用 `runner/core/native_factory.py`、`runner/core/native_runner.py` 和 `runner/core/live_provider.py`。Candidate 生成与 Gold 评测保持物理生命周期分离：Target 和 Provider 关闭之后，Evaluator 才允许加载 Gold。
