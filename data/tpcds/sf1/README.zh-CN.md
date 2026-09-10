# TPC-DS SF1 运行数据

[English](README.md) | [简体中文](README.zh-CN.md)

默认本地数据库是本目录中的 `tpcds.duckdb`。数据库文件和生成的 `.dat` 输入都是可复现的运行产物，不会提交到仓库。

可以通过 `BENCHMARK_DATABASE_URL` 指向另一个 DuckDB 文件或受支持的其他 Adapter。数据集身份由 SF1 Manifest 和校验和确定，不依赖引擎或文件路径。

使用官方工具生成 SF1 `.dat` 文件并放入 `generated/` 后，执行：

```bash
python -m scripts.load_tpcds_sf1 --generator-binary /path/to/dsdgen
```

Loader 会创建全部 25 张物理表，处理 `dsdgen` 输出末尾的分隔符，并写出符合 [`runner/contracts/dataset-manifest.schema.json`](../../../runner/contracts/dataset-manifest.schema.json) 的 Manifest。其中包括 Generator Binary Hash、DuckDB 版本、Schema 与数据库 Hash、逐表行数和源文件 Hash，以及与本地路径无关的逻辑 `dataset_sha256`。24 表语义基准不包含 `dbgen_version`，该表继续用作 Generator Metadata。

Loader 会在创建数据库前确认 25 个输入全部存在，而且除非显式传入 `--overwrite`，否则不会替换已有数据库。本地开发时可以省略 `--generator-binary`，但缺少该 Hash 的 Manifest 不能通过结果发布 Preflight。`--generator-version` 默认为 `4.0.0`，必须与生成 `.dat` 文件所用的官方工具包一致。

加载完成后，校验全部 25 个源文件 Hash、Schema 与数据库身份、逻辑快照 Hash、DuckDB 版本和数据库实际表行数，然后冻结 Evaluator-only q01 结果身份：

```bash
python -m scripts.freeze_tpcds_sf1 --require-sources
```

该命令写入 `benchmark/tpcds/results/gold/sf1/q01.json`，其中只有列名、行数和标准化结果 SHA-256，不包含结果行。使用 `--validate-only` 可以只执行快照 Gate 而不写入 Gold；`--development` 允许本地绝对路径和缺失 Generator Hash，但产物不能提交或发布。
