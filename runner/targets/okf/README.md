# OKF native consumer

[English](README.md) | [简体中文](README.zh-CN.md)

`OkfNativeConsumer` evaluates an OKF bundle in its native form: original
Markdown, YAML frontmatter, indexes, and local links. It is not a semantic
engine and it does not execute queries or translate the bundle into a shared
retrieval representation.

## Boundary

The consumer exposes only the registry-declared OKF operations:

- `okf.validate_frontmatter`
- `okf.validate_links`
- `okf.list_files`
- `okf.read_file`
- `okf.follow_link`
- `okf.search_text`

`search_text` is an explicit literal scan of source Markdown, never an
embedding index. The consumer has no database dependency and does not expose a
SQL fallback. Each file read returns its SHA-256 and access telemetry records
sanitized operation metadata, artifact identity, duration, and result count.

## Isolation rules

- The artifact root is checked before the consumer starts; evaluator-only and
  Gold roots are rejected.
- Every supplied path must be bundle-relative, Markdown-only, and resolve under
  the declared root. Absolute paths, `..`, symlinks, and symlink escapes fail
  closed.
- Link following is permitted only for a local link actually declared in the
  source document.
- Construction performs no bundle scan. Files are read only for an explicit
  operation, so no preload-all context is available to an agent.

The adapter is a protocol component only. It creates no score, run record, or
official result and must be paired with the separate evaluator-only component.
