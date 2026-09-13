# Cube REST adapter

[English](README.md) | [简体中文](README.zh-CN.md)

`CubeRestAdapter` is the benchmark's target-specific integration for Cube's
REST Query API. It exposes only the native REST surfaces declared in
`runner/config/targets.native.yaml`:

- preflight: `GET /readyz`, then `GET /cubejs-api/v1/meta`;
- agent-visible operations: `cube.meta` and `cube.load`.

`cube.load` sends a JSON REST query object as the standard `query` parameter to
`GET /cubejs-api/v1/load`. The adapter deliberately does not expose Cube SQL,
DuckDB, or any other fallback.

## Runtime identity

Construct the adapter with a non-empty Cube `runtime_identity` and a pinned,
lowercase image digest in the form `sha256:<64 hexadecimal characters>`. These
are required before any network request. A tag such as `latest` is not a valid
benchmark runtime identity.

The adapter accepts an optional API token but it never includes it in request or
response artifacts. Artifacts contain only the operation, HTTP method, path,
status, content type, and top-level JSON keys. Result rows are returned only in
memory through the native response payload.

## Failure policy

Timeouts return `timeout`; unavailable native endpoints (404, 405, 501) return
`unsupported`; other transport/protocol failures return `error`. None of those
states executes SQL or a database fallback. The deterministic unit tests use a
fake HTTP transport and do not claim a live Cube result.
