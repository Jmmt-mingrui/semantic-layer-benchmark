# Runner 配置

[English](README.md) | [简体中文](README.zh-CN.md)

所有被测系统使用同一份运行时数据库配置。默认本地引擎是 DuckDB，但无需修改 canonical questions 或指标即可替换连接。

当前目录包含三类不同输入：

| 文件 | 作用 |
| --- | --- |
| [`database.yaml`](database.yaml) | 所有目标共享的只读数据库连接契约 |
| [`targets.native.yaml`](targets.native.yaml) | 每个条件的原生产物、操作 Allowlist、Fallback 和 Readiness 定义 |
| [`native-sf1-q01.yaml`](native-sf1-q01.yaml) | 只选择一个实例化 q01 和空白上下文基线的契约 Pilot |

Experiment 和产物结构见 [`../contracts/`](../contracts/)，全新对话的准确行为见 [`../prompts/`](../prompts/)。

## 数据库连接

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `BENCHMARK_DATABASE_URL` | `duckdb:///./data/tpcds/sf1/tpcds.duckdb` | 驱动相关连接 URL 或数据库位置 |
| `BENCHMARK_DATABASE_CATALOG` | 未设置 | 可选 catalog/database namespace |
| `BENCHMARK_DATABASE_SCHEMA` | `main` | 存放 TPC-DS 表的 schema |

密钥不得提交到仓库。适配器可以替换 `driver` 和 `dialect`，但必须保持相同的 SF1 manifest、逻辑关系名、canonical 指标和只读策略。

`benchmark/tpcds/sql/reference/postgres/` 中的 PostgreSQL SQL 继续作为带出处的结果 oracle 和公式参考，但不再定义运行时连接。DuckDB 翻译放在 `benchmark/tpcds/sql/reference/duckdb/`，并且必须通过结果等价校验。

原生语义模型在部署或适配器渲染时解析物理 namespace；canonical 层不依赖 catalog 或 schema 名称。

使用 `pip install -e '.[test]'` 安装运行和测试依赖。`runner.core.database.connect()` 当前注册 DuckDB，并统一返回列名、结果行和执行耗时；其他数据库驱动可以实现同一边界，而无需修改 benchmark 输入。

## 原生目标策略

Harness 只允许在原生操作外增加超时、安全、脱敏和 Telemetry，不能在主赛道开始前把 MetricFlow、Cube、Ossie、OKF 或 Skill 转换为共享文本。`blank_context` 可以调用数据库发现工具，但不预加载 Schema；`ddl_only` 可以看到 DDL，并且单独报告。

Readiness 必须显式记录。标记为 `*_pending` 的目标不能静默跳过，也不能改走直接 SQL。只有在原生模型、固定版本、Health Check 和 Adapter 全部存在后，Preflight 才允许它运行。
