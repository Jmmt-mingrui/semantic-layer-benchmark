# TPC-DS-derived SF1 运行数据

[English](README.md) | [简体中文](README.zh-CN.md)

Benchmark 使用本地 TPC-DS-derived scale-factor-1 数据集。它不是经过 TPC 审计的官方 Benchmark 结果，本仓库产生的数据不得表述为官方 TPC-DS 结果，也不能与官方公布结果直接比较。

生成的 `.dat` 文件和 DuckDB 数据库都是可复现的本地运行产物，Git 会显式忽略它们。

## 1. 使用官方 4.0.0 Toolkit 生成 SF1

从 TPC 官方发行渠道获取并构建 TPC-DS Tools v4.0.0，然后把生成的 `dsdgen` 传给仓库脚本：

```bash
python -m scripts.generate_tpcds_sf1 \
  --dsdgen /path/to/TPC-DS-v4.0.0/tools/dsdgen
```

该脚本执行等价命令：

```text
dsdgen -scale 1 -dir <local-output> -force
```

并在本地记录 Generator Binary SHA-256 等生成信息；生成数据不会提交到仓库。

## 2. 加载并固定 DuckDB Snapshot 身份

```bash
python -m scripts.load_tpcds_sf1 \
  --generator-version 4.0.0 \
  --generator-binary /path/to/TPC-DS-v4.0.0/tools/dsdgen
```

Loader 创建全部 25 张物理表，处理 `dsdgen` 输出末尾分隔符，并写出符合 [`runner/contracts/dataset-manifest.schema.json`](../../../runner/contracts/dataset-manifest.schema.json) 的 `manifests/duckdb-sf1.json`。Manifest 包含 Generator 版本与 Binary Hash、DuckDB 版本、Schema/数据库 Hash、所有输入文件 Hash、逐表行数，以及与本地路径无关的逻辑 `dataset_sha256`。24 表语义 Benchmark 不包含 `dbgen_version`，该表继续作为 Generator Metadata。

发布前验证会重新 Hash Schema、数据库和生成输入，校验逻辑 Snapshot Identity、当前 DuckDB 版本和全部表实际行数。缺少 `dsdgen` Binary Hash 的 Manifest 不能通过发布 Gate。

## 3. 冻结 representative-v1 Gold Pack

代表集包含 q01、q02、q03、q05、q12、q14、q21、q36、q39、q49、q75、q84。不可变 Question Instances 位于 `benchmark/tpcds/questions/instances/sf1-representative-v1.jsonl`。

本地 SF1 数据库准备好后执行：

```bash
python -m scripts.freeze_representative_sf1
python -m scripts.freeze_representative_sf1 --verify
```

Freeze 命令会在同一个已验证 Snapshot 上执行所有固定的 DuckDB Reference SQL。q14 和 q39 各包含两条必须返回的 Statement，但在 Execution Accuracy 分母里仍各算一道问题。每个 Evaluator-only Gold Artifact 会绑定：

- Dataset Manifest SHA-256、逻辑数据集 Identity 和数据库 SHA-256；
- 精确的 Question Instance 行 Hash；
- 每个 Reference SQL 的路径和 SHA-256；
- 结果列定义、行数和标准化结果 SHA-256。

Gold 永远不写入原始结果行。Dataset Manifest、代表题实例、Reference SQL 或 Gold 文件任意发生变化，验证都会 fail closed。

旧的 `scripts.freeze_tpcds_sf1` q01-only 流程继续保留用于兼容；代表集实验应使用 `scripts.freeze_representative_sf1`。
