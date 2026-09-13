# 原生目标 Adapter

[English](README.md) | [简体中文](README.zh-CN.md)

本目录存放目标特定的 Benchmark Adapter，并非共享的语义 API。每个 Adapter
只能暴露目标已声明的原生操作，保留原生请求形状；不得直接 SQL 或跨目标
fallback，遇到不满足约定的情况必须 fail-closed。

## Skill Host Adapter

`SkillHostAdapter` 将
`semantic-models/skill/tpcds-sf1-table-semantics` 作为原生 Skill package
挂载。发现阶段只暴露 frontmatter 推导的元数据，以及不可变 package/host
revision identity；不会枚举或读取 `SKILL.md` 和任何 reference。

Agent 必须显式调用 `skill.activate`，Host 才会加载完整 `SKILL.md`。激活后，
`skill.read_reference` 每次仅按需读取一个 UTF-8 且相对 package 的文件。Host
会拒绝路径穿越、绝对路径、package symlink、evaluator/Gold 路径、预加载全部
reference、共享 chunk 转换和未声明 fallback。访问 telemetry 只记录 operation、
脱敏相对路径、字节数、SHA-256 与耗时；绝不记录文档内容、SQL、结果或 Gold 数据。

该 Adapter 不产生分数。SQL 执行与评估仍是独立且显式声明的 Benchmark 操作。
