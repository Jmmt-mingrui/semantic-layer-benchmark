# TPC-DS-derived SF1 运行数据

[English](README.md) | [简体中文](README.zh-CN.md)

Benchmark 使用本地 TPC-DS-derived scale-factor-1 数据集。它不是经过 TPC 审计的官方 Benchmark 结果，本仓库产生的数据不得表述为官方 TPC-DS 结果，也不能与官方公布结果直接比较。

生成的 `.dat` 文件和 DuckDB 数据库都是可复现的本地运行产物，Git 会显式忽略它们。

## 前置条件：取得官方工具包

TPC 在[当前规范页面](https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp)列出了 TPC-DS Tools v4.0.0。下载页面要求每位用户阅读并接受 TPC Tools 许可证、登记邮箱，并使用 TPC 邮件发送的链接下载。因此，本仓库及其自动化不会下载、镜像或再分发该工具包。

下载官方压缩包后，按照包内构建说明编译；在受支持的 Linux 目录结构中，通常是在 tools 目录运行 `make OS=LINUX`。发布级实验不得用 DuckDB 内置生成器、容器镜像或第三方镜像替代，因为这会改变被记录的 Generator Provenance。

## 推荐：运行完整准备流水线

在安装 `.[test]` 的全新 Checkout 中，一条命令会生成 SF1、构建 DuckDB Snapshot、冻结全部 12 个代表问题的 Gold Identity、完成验证，并运行 Benchmark Lint 和测试：

```bash
python -m scripts.prepare_tpcds_sf1 \
  --dsdgen /path/to/TPC-DS-v4.0.0/tools/dsdgen
```

仅在明确要替换已有本地 Snapshot 时使用 `--overwrite`。成功后，命令会输出 Generator、逻辑 Dataset、数据库与 Gold Pack Hash，以及表数、总行数、问题数和 Statement 数；实验记录应保留这段终端输出。

工具包、生成的 `.dat`、DuckDB 数据库和本地 Dataset Manifest 均不提交。Gold 文件只包含 Hash 和结果元数据，绝不包含结果行。

## 分步执行

### 1. 使用官方 4.0.0 Toolkit 生成 SF1

若需分步执行，先运行仓库内的生成 Wrapper：

```bash
python -m scripts.generate_tpcds_sf1 \
  --dsdgen /path/to/TPC-DS-v4.0.0/tools/dsdgen
```

该脚本执行等价命令：

```text
dsdgen -scale 1 -dir <local-output> -force
```

并在本地记录 Generator Binary SHA-256 等生成信息；生成数据不会提交到仓库。

### 2. 加载并固定 DuckDB Snapshot 身份

```bash
python -m scripts.load_tpcds_sf1 \
  --generator-version 4.0.0 \
  --generator-binary /path/to/TPC-DS-v4.0.0/tools/dsdgen
```

Loader 创建全部 25 张物理表，处理 `dsdgen` 输出末尾分隔符，并写出符合 [`runner/contracts/dataset-manifest.schema.json`](../../../runner/contracts/dataset-manifest.schema.json) 的 `manifests/duckdb-sf1.json`。Manifest 包含 Generator 版本与 Binary Hash、DuckDB 版本、Schema/数据库 Hash、所有输入文件 Hash、逐表行数，以及与本地路径无关的逻辑 `dataset_sha256`。该逻辑身份覆盖 24 张语义 Benchmark 表；`dbgen_version` 的生成行包含墙钟时间和本地命令路径，因此只作为受校验的 Generator Metadata。

发布前验证会重新 Hash Schema、数据库和生成输入，校验逻辑 Snapshot Identity、当前 DuckDB 版本和全部表实际行数。缺少 `dsdgen` Binary Hash 的 Manifest 不能通过发布 Gate。

### 3. 冻结 representative-v1 Gold Pack

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
