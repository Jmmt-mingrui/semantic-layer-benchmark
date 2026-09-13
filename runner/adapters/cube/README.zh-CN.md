# Cube REST Adapter

[English](README.md) | [简体中文](README.zh-CN.md)

`CubeRestAdapter` 是 benchmark 对 Cube REST Query API 的目标专属接入。它只暴露
`runner/config/targets.native.yaml` 声明的原生 REST surface：

- preflight：`GET /readyz`，然后 `GET /cubejs-api/v1/meta`；
- 对 Agent 可见的操作：`cube.meta` 和 `cube.load`。

`cube.load` 把 JSON REST query object 作为标准 `query` 参数发送给
`GET /cubejs-api/v1/load`。该 Adapter 刻意不暴露 Cube SQL、DuckDB 或其他 fallback。

## Runtime identity

构造 Adapter 时必须提供非空的 Cube `runtime_identity`，以及固定的小写镜像摘要，格式为
`sha256:<64 个十六进制字符>`。两者都在任何网络请求前校验。诸如 `latest` 的 tag 不能作为
benchmark 的 runtime identity。

Adapter 可选接收 API token，但绝不会把它写入 request 或 response artifact。artifact 仅记录
操作名、HTTP 方法、路径、状态、content type 和顶层 JSON key。结果行只通过原生 response payload
在内存中返回。

## 失败策略

超时返回 `timeout`；原生 endpoint 不可用（404、405、501）返回 `unsupported`；其他
transport/protocol 失败返回 `error`。这些状态都不会执行 SQL 或数据库 fallback。确定性单元测试
使用 fake HTTP transport，不声明真实 Cube 的运行结果。
