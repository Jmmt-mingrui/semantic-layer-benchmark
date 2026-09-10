# TPC-DS SF1 运行数据

[English](README.md) | [简体中文](README.zh-CN.md)

默认本地数据库是本目录中的 `tpcds.duckdb`。数据库文件和生成的 `.dat` 输入都是可复现的运行产物，不会提交到仓库。

可以通过 `BENCHMARK_DATABASE_URL` 指向另一个 DuckDB 文件或受支持的其他 Adapter。数据集身份由 SF1 Manifest 和校验和确定，不依赖引擎或文件路径。

使用官方工具生成 SF1 `.dat` 文件并放入 `generated/` 后，执行：

```bash
python scripts/load_tpcds_sf1.py --generator-binary /path/to/dsdgen
```

Loader 会创建全部 25 张物理表，处理 `dsdgen` 输出末尾的分隔符，并写出符合 [`runner/contracts/dataset-manifest.schema.json`](../../../runner/contracts/dataset-manifest.schema.json) 的 Manifest。其中包括 Generator Binary Hash、DuckDB 版本、Schema 与数据库 Hash、逐表行数和源文件 Hash，以及与本地路径无关的逻辑 `dataset_sha256`。24 表语义基准不包含 `dbgen_version`，该表继续用作 Generator Metadata。

本地开发时可以省略 `--generator-binary`，但缺少该 Hash 的 Manifest 不能通过结果发布 Preflight。`--generator-version` 默认为 `4.0.0`，必须与生成 `.dat` 文件所用的官方工具包一致。
