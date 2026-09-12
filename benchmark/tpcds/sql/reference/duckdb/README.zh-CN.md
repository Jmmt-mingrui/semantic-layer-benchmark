# DuckDB Reference SQL

[English](README.md) | [简体中文](README.zh-CN.md)

本目录保存带出处的 PostgreSQL Result-oracle Query 的 DuckDB 转换。每份转换必须保留 Query ID、来源元数据、参数和预期语义，并记录每一项方言改写。

只有在固定的 SF1 Manifest 上执行并产生等价的归一化结果后，Query 才能标记为通过结果校验。q01–q10 当前可以在 DuckDB 1.4.0 空 Schema 上执行且无需文本改写；详情见 [`validation.yaml`](validation.yaml) 和 [`SOURCE.md`](SOURCE.md)。
