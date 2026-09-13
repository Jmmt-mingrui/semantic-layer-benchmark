# Benchmark 维护命令

[English](README.md) | [简体中文](README.zh-CN.md)

仓库维护命令以 Python 模块提供，从干净 Checkout 运行时行为保持一致。安装 `.[test]` 后，在仓库根目录执行。

## Benchmark lint

```bash
python -m scripts.benchmark_lint
```

该命令复用现有的序列化文件、Canonical Question 和原生目标校验，并增加仓库级 Benchmark 不变量：

- Canonical q01–q99 定义和 Reference SQL 保持完整；
- 每个作为英文默认入口的 `README.md` 都有 `README.zh-CN.md`，反向也必须成对；
- 原生目标保留原生产物、全新会话和封闭操作集合，可执行引擎不能静默回退到直接 SQL；
- 目标可见的 Artifact 或工具目录不能与 Evaluator-only Question 或 Gold Identity 重叠；
- 生成的 SF1 数据、数据库、运行输出、Trace、报告和原始结果行不能被提交。

排查问题时可以只运行一个或多个检查：

```bash
python -m scripts.benchmark_lint --check target-isolation
python -m scripts.benchmark_lint --check readme-pairs --check artifact-hygiene
```

Git 可用时，lint 读取已跟踪文件集合。因此，本地生成且被正确忽略的 SF1 文件不会让仓库卫生检查失败；把它们加入 Git 才会失败。

`validate_repository.py` 仍是原有 Conformance Check 的唯一实现。Lint 直接导入这些检查，再补充 Benchmark 不变量，不重新实现同一套逻辑。
