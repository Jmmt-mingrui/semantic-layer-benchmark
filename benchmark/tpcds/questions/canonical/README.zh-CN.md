# Canonical TPC-DS 问题

[English](README.md) | [简体中文](README.zh-CN.md)

`questions.jsonl` 为 99 个 TPC-DS Query Template 各定义一个 Benchmark Task，并记录如何回溯到规范章节和可审查的 SQL。

这些问题是根据 TPC-DS v4.0.0 Template 的功能意图编写的原创、简洁释义，并非规范中 Business Question 的复制。Template Input 保持为符号参数，便于之后使用 Qualification Value 或生成值实例化同一份问题定义。

每条 JSONL 记录包含：

- `id`：稳定的 Benchmark 标识（`q01` 到 `q99`）
- `source_template`：对应的官方 TPC-DS Toolkit Template
- `question`：Canonical 英文问题
- `parameters`：实例化任务所需的符号输入
- `multi_statement`：Template 14、23、24 和 39 为 `true`，因为它们各包含两条相关 SQL Statement
- `source`：TPC-DS 规范版本、Appendix B 章节、规范 URL、Toolkit URL 和官方 Template 路径
- `reference_sql`：本地 PostgreSQL SQL、固定的上游仓库与 Commit、上游文件 URL、许可证和适配来源

## 来源层级

1. 业务意图和编号来自 [TPC-DS v4.0.0 规范](https://www.tpc.org/tpc_documents_current_versions/pdf/tpc-ds_v4.0.0.pdf) Appendix B。
2. 功能定义以[官方 TPC-DS Toolkit 下载](https://www.tpc.org/TPC_Documents_Current_Versions/download_programs/tools-download-request5.asp?bm_type=TPC-DS&bm_vers=4.0.0&mode=CURRENT-ONLY)中的 `query_templates/queryN.tpl` 为准。Toolkit 按 TPC EULA 分发，因此仓库不复制官方 Template。
3. 可审查 SQL 存放在 `../../sql/reference/postgres/`。这些是使用固定替换值的 TPC-DS 派生 PostgreSQL Qualification SQL，并非官方 Template 原文。参见该目录的 `SOURCE.md` 及每个 SQL 文件的 Header。

当自然语言问题、Business Question 描述和 SQL 不一致时，以官方 Toolkit Template 定义的查询行为为准。
