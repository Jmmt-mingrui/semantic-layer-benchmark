# Evaluator-only SF1 Gold Identity

[English](README.md) | [简体中文](README.zh-CN.md)

本目录保存结果身份，不保存结果行。每个 Gold Artifact 会把一个实例化问题和参考 SQL 绑定到一份已经验证的 TPC-DS 派生 SF1 数据 Manifest，并记录标准化结果 SHA-256、列名和行数。

任何被测目标都不得挂载或读取本目录。只有目标对话关闭并提交最终 Result Handle 后，Evaluator 才能打开 Gold Identity。

在官方 TPC-DS v4.0.0 `dsdgen` Binary 和全部 25 个 SF1 输入通过发布 Preflight 前，仓库不会包含 `q01.json`。生成命令：

```bash
python -m scripts.freeze_tpcds_sf1 --require-sources
```

Development Mode 只用于测试和本地诊断，其输出不能提交，也不能作为 Benchmark 结果发布。
