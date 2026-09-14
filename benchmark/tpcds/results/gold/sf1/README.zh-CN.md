# Evaluator-only SF1 Gold Identity

[English](README.md) | [简体中文](README.zh-CN.md)

本目录只保存结果身份，不保存任何原始结果行。任何被测 Target 都不得挂载或读取本目录；只有 Target 与 Provider 会话关闭之后，Evaluator 才允许加载 Gold。

发布目标是 `representative-v1/`：q01、q02、q03、q05、q12、q14、q21、q36、q39、q49、q75、q84 各有一个问题级 Gold Artifact，并附带 Pack Manifest。q14 和 q39 各绑定两条必须执行的 Reference Statement，但在问题级 Accuracy 分母中仍各算一道题。

每个冻结 Artifact 都绑定精确的 TPC-DS-derived SF1 Dataset Manifest、数据库 Identity、Question Instance 行 Hash、每条 Reference SQL SHA-256，以及结果列、行数和标准化结果 SHA-256。任何输入变化都会使 `--verify` fail closed。

在本地提供官方 TPC-DS v4.0.0 `dsdgen` Binary、生成完整 SF1 输入并通过发布 Preflight 之前，仓库不会伪造或提交 representative Gold 文件。生成与验证命令：

```bash
python -m scripts.freeze_representative_sf1
python -m scripts.freeze_representative_sf1 --verify
```

Development Mode 只用于测试/本地诊断，不能作为发布 Benchmark 结果。旧 q01-only Freeze 命令继续保留用于兼容。
