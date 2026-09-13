# 原生 Adapter

[English](README.md) | [简体中文](README.zh-CN.md)

此目录包含窄范围、目标特定的 Adapter，而不是共享语义查询 API：每个模块都保留目标系统文档中定义的操作名和 payload 形状，目标不可用时绝不能改走直接 SQL。

## MetricFlow

[`metricflow.py`](metricflow.py) 只封装
[`../config/targets.native.yaml`](../config/targets.native.yaml) 固定源码版本对应的官方 `mf` CLI：

| Benchmark 操作 | 固定的原生命令 |
| --- | --- |
| `metricflow.health_checks` | `mf health-checks` |
| `metricflow.validate_configs` | `mf validate-configs` |
| `metricflow.list_metrics` | `mf list metrics` |
| `metricflow.list_dimensions` | `mf list dimensions --metrics <逗号分隔>` |
| `metricflow.list_dimension_values` | `mf list dimension-values --metrics <…> --dimension <…>` |
| `metricflow.list_entities` | `mf list entities --metrics <逗号分隔>` |
| `metricflow.query` | `mf query --metrics <逗号分隔> …` |

实现固定在 MetricFlow commit
[`8750c1d`](https://github.com/dbt-labs/metricflow/tree/8750c1dfe79c9d92e37fc9b8542d544e29f8852e)，该版本的包版本号为 `0.213.0.dev0`。上表命令来自该 commit 的官方 CLI 实现，并非根据引擎源码自行拼装。

任何请求前，Adapter 都要求 version probe、source model-layout 检查、`health-checks` 和 `validate-configs` 全部成功。命令在外部准备好的兼容 dbt runtime project 中执行，同时独立记录仓库固定的 standalone model root。这一区分是刻意的：仓库中的 standalone authoring 文件本身不能证明已经配置好了可运行的 dbt/MetricFlow 环境。

每个响应都保存原始 argv、退出码、stdout/stderr、耗时以及确定性的 SHA-256 request/response identity。Adapter 不会打开数据库连接、生成 SQL、调用 `db.execute_readonly` 或暴露 Gold artifact。可识别的缺失 MetricFlow metric/dimension/entity 会记录为 `unsupported`；其他非零 CLI 退出一律记录为 `failed`。

单元测试使用 fake subprocess boundary，不声称 CI 中已经安装或执行了 MetricFlow。
