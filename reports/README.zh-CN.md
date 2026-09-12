# 离线运行报告

[English](README.md) | [简体中文](README.zh-CN.md)

离线报告生成器把已经完成的 Benchmark 产物转换成确定性的 JSON 和 Markdown 摘要。它严格位于 Benchmark 边界的下游：不导入任何引擎 Adapter、不打开数据库、不执行 SQL，也不读取 evaluator-only Gold 资产。

## 接受的输入

生成器只接受一个已完成的 `run.json`、该 Run 引用的所有 `trial.json`，以及每个 Trial 同目录下的 `trace.jsonl`。写出任何文件之前，它会：

- 使用仓库中的 JSON Schema Draft 2020-12 契约和 Format Checker 校验全部记录；
- 将 Trial 引用限制在该 Run 的 `trials/` 目录内，并拒绝符号链接或路径穿越；
- 校验 Run、Experiment、Trial 身份，Trial 引用和 ID 的唯一性，连续的 Trace 序号、生命周期端点及 Parent 顺序；
- 校验 Run Summary 与实际加载的 Trial 状态一致。

生成器不会解引用 Conversation、SQL、Candidate Result、原生请求/响应、Error 或 Answer Artifact。报告环境可以看不到这些引用指向的文件。

## 输出

`report.json` 和 `report.md` 包含：

- passed、failed、unsupported、invalid、timeout 和 skipped 的数量；
- 仅以可评测 Trial 为分母的准确率，即 `passed / (passed + failed)`；
- Evaluator 错误分类数量；
- Provider Token 的覆盖率和已知总量，未知值不会被转换为零；
- Tool、Database 和 Native Service 调用的覆盖率及已知总量；
- Trial 与 Trace Event 延迟分布；
- 原生操作的数量、状态和延迟分布；
- 校验数量及 Run 的可复现性身份。

P50 是中位数，P95 使用 nearest-rank。报告不会进行目标排名或声称统计显著性；跨目标聚合与置信区间属于后续分析层。

## 使用方法

在仓库根目录运行：

```bash
python -m scripts.generate_run_report \
  --artifact-root . \
  --run runs/<run-id>/run.json \
  --output-dir reports/generated/<run-id>
```

Markdown 默认使用英文。传入 `--language zh-CN` 可生成中文 Markdown。已有输出默认受保护；只有明确希望替换时才使用 `--overwrite`。

该命令只适用于已结束、且符合当前 `0.1.0` 契约的协议测试或 Benchmark Run。任一输入无效时，它会 fail closed，不写出任何报告。
