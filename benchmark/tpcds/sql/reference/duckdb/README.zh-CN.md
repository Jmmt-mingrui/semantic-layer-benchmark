# DuckDB Reference SQL

[English](README.md) | [简体中文](README.zh-CN.md)

本目录保存带出处的 PostgreSQL Result-oracle Query 的 DuckDB 转换。每份转换必须保留 Query ID、来源元数据、参数和预期语义，并记录每一项方言改写。

只有在固定 SF1 Manifest 上执行并产生等价归一化结果后，Query 才能标记为通过结果校验。q01–q10 最初通过 DuckDB 1.4.0 空 Schema 执行且无需文本改写。公开输出修订新增已声明的别名与确定性排序 tie-break，见 [`validation.yaml`](validation.yaml) 和 [`SOURCE.md`](SOURCE.md)。全部 14 条代表题语句已有契约校验；这不代表 SF1 准确率测试完成。
