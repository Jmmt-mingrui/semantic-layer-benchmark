# TPC-DS 形状的合成协议 Fixture

[English](README.md) | [简体中文](README.zh-CN.md)

本目录提供仅用于测试的支持代码：在官方生成数据尚不可用时，CI 可以用它验证数据库、Adapter 和 Artifact 协议。

`create_synthetic_tpcds_fixture()` 会创建仓库定义的 25 张 DuckDB 物理表，并向每张表写入恰好一行确定性的合成数据。整数代理键使用同一个哨兵值，因此可以执行轻量 Join Path 测试。固定 Schema 与 Fixture Revision 下的逻辑身份保持稳定；DuckDB 文件字节不被视为可移植身份。

## 强制边界

这个 Fixture **不是 TPC-DS 数据、不是 SF1、不是任何 Scale Factor 的数据集，也不是正确性 Oracle**。它的 Sidecar Identity 始终声明：

- `publishable: false`；
- `ranking_eligible: false`；
- `tpcds_equivalence: none`；
- `scale_factor: null`；
- `gold_results: forbidden`。

生成器拒绝写入 `data/tpcds/sf1/`、`benchmark/tpcds/results/gold/`、`runs/` 或 `reports/generated/`，而且绝不会生成 Dataset Manifest 或 Gold Result。基于该 Fixture 的结果只能用于协议和 CI 断言，绝不能合入 Benchmark 分数、比较、图表或结论。

## 测试用法

请在测试框架提供的临时目录中创建数据库：

```python
def test_adapter_protocol(tmp_path):
    database = tmp_path / "protocol.duckdb"
    identity = create_synthetic_tpcds_fixture(database, repository_root=REPOSITORY_ROOT)
    assert identity["ranking_eligible"] is False
```

任何可发布的执行正确性实验必须使用 [`data/tpcds/sf1/README.zh-CN.md`](../../data/tpcds/sf1/README.zh-CN.md) 中记录的官方 `dsdgen` v4.0.0 流程。
