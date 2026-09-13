# Native target adapters

[English](README.md) | [简体中文](README.zh-CN.md)

This directory contains target-specific benchmark adapters. It is not a shared
semantic API: each adapter exposes only the target's declared native operations,
preserves native request shapes, and must fail closed instead of using a direct
SQL or cross-target fallback.

## Skill host adapter

`SkillHostAdapter` hosts
`semantic-models/skill/tpcds-sf1-table-semantics` as a native Skill package.
At discovery, it exposes only frontmatter-derived metadata and immutable package
and host revision identities. It does not enumerate or load `SKILL.md` or any
reference.

The agent must explicitly invoke `skill.activate`; only then does the host load
the complete `SKILL.md`. After activation, `skill.read_reference` reads exactly
one requested UTF-8 package-relative file. The host rejects traversal, absolute
paths, package symlinks, evaluator/Gold paths, preload-all operations, shared
chunk conversion, and undeclared fallbacks. Its access telemetry contains only
operation, sanitized relative path, byte count, SHA-256, and duration -- never
document content, SQL, results, or Gold data.

No score is produced by this adapter. SQL execution and evaluation remain
separate, explicitly declared benchmark operations.
