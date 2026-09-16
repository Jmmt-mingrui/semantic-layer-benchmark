# 本地多题、多目标评测说明

本补丁基于仓库 `859d4a2`。默认小规模探索，不宣称完整 benchmark 结论。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
cp .env.example .env.local
```

编辑 `.env.local`：填入实际模型名、HTTPS 服务地址和新 API Key。
地址可以写到 `/compatible-mode/v1`，入口会补齐 `/chat/completions`。
不要继续使用曾在聊天里明文发出的密钥。不要把 `.env.local` 提交到 Git。
`--env-file` 只读取字面量，不执行 shell；已有环境变量优先于文件。

## 准备官方 SF1 数据

工具包需要用户自己接受 TPC 许可后取得，本补丁不分发它。
Linux：解压 TPC-DS 4.0.0，进入工具包 `tools`：

```bash
make OS=LINUX LINUX_CFLAGS='-O2 -fcommon' dsdgen
```

macOS / 新版 Clang：若没有 `makefile` 或 `Makefile`，先执行
`cp Makefile.suite Makefile`。在 tools 下通过编辑器添加两个兼容头文件：

`malloc.h`：

```c
#include <stdlib.h>
```

`values.h`：

```c
#include <limits.h>
#include <float.h>
#ifndef MAXINT
#define MAXINT INT_MAX
#endif
```

再构建：

```bash
make OS=LINUX LINUX_CFLAGS='-std=gnu89 -O2 -fcommon -I.' dsdgen
```

这些是审计附件提供的 macOS 兼容步骤，本次未在 macOS 复测。
回到仓库根目录，执行：

```bash
python -m scripts.prepare_tpcds_sf1 --dsdgen /绝对路径/tools/dsdgen
```

预留至少 6 GB 可用磁盘，包含 .dat、DuckDB 和临时空间。
生成器自动使用短的相对 `-dir` / `-distributions` 参数，避免 TPC-DS 4.0.0
80 字节参数缓冲区问题；最终 .dat 仍在仓库内部，满足 Gold 冻结门禁。
已有数据时不要随意加 `--overwrite`。

如果数据已生成和加载，只需要：

```bash
python -m scripts.freeze_representative_sf1
python -m scripts.freeze_representative_sf1 --verify
```

## 这次修订与原约定的关系

上一补丁没有修复 representative 题面欠定义，新版已补齐 12 题的列名/列序、排序方向/NULL 位置、Limit 和双结果顺序；q01 与 qualification 的完整措辞统一。题目还写清同店平均、日期两端包含、比值方向及原 SQL 的重复行语义。

| 原约定 | 当前行为 |
|---|---|
| 正确性必需的列、分组、排序、Limit 写进问题 | 全部代表题公开声明；lint 对照绑定列与最外层 SQL 校验 |
| Agent 只收到 target_input.question | 保持；参考 SQL、Gold 行/Hash、参数元数据不发送给 Agent |
| 原生路径、同一快照、全新对话 | 保持；不换数据库、不降级 MetricFlow 为 Agent SQL |
| 严格结果比较 | 保持 exact_normalized/canonical-json-v1；不按名重排列、不重排行、不加容差 |
| 正式报告要求 216 条完整记录 | 保持；本地子集不冒充正式结果 |

代表题实例升级为 schema v0.3.0 / `public-output-contract-v1` 并更换实例 ID；q14/q39 的两个契约按提交顺序列在 `result_contract.statements`。q02/q14/q39 输出新增明确别名，q36/q75 新增确定性排序 tie-break，已记录在 `benchmark/tpcds/sql/reference/duckdb/SOURCE.md`。这会改变实例/SQL/结果 Hash，**旧 Gold 和旧成绩不能直接沿用**。不需要重新生成数据，但必须在原 SF1 快照上重新执行上面的冻结和验证命令。只检查旧包会因 Hash 不一致失败，这是预期行为。

```bash
python -m scripts.materialize_representative_questions
python -m scripts.benchmark_lint --check question-output-contracts
```

## 先跑 3 题 × 2 对照组

```bash
semantic-benchmark run-live --env-file .env.local \
  --questions q01 q02 q03 --targets blank_context ddl_only \
  --repetitions 1 --timeout 120 --save-details
```

这是 6 个独立试验，每个试验使用全新对话。每题会立即显示状态并保存进度。
`--timeout` 是每次模型请求的超时，不是整个试验的时限。
默认最多 12 轮、每轮输出预算 4096；推理模型的 reasoning token 也消耗输出预算，
不要用 16-token 的 smoke 测试断定模型不可用。

兼容之前的命令：

```bash
python -m scripts.run_local_q01 --env-file .env.local \
  --questions q01 q02 q03 --targets ddl_only --timeout 120 --save-details
```

## 增加知识表示目标

```bash
semantic-benchmark run-live --env-file .env.local \
  --questions q01 q02 q03 --targets ddl_only ossie okf skill \
  --repetitions 1 --timeout 120 --save-details
```

Skill 需要 `BENCHMARK_SKILL_HOST_REVISION` 标记实际宿主版本；模板标记本仓库原生宿主实现。
OKF 的规范版本审查请记录实际审核的 commit，不要为了通过门禁随意伪造 pin。
Ossie 是模型交换格式，不是 SQL 引擎：它由 Agent 消费原始 YAML 后写 SQL。

MetricFlow 只有外部 dbt runtime 真实准备并通过 preflight 后才能评测：

```bash
semantic-benchmark run-live --env-file .env.local --questions q01 \
  --targets metricflow --metricflow-runtime /绝对路径/dbt-project \
  --metricflow-executable /绝对路径/venv/bin/mf --save-details
```

固定源码 commit 是 `8750c1dfe79c9d92e37fc9b8542d544e29f8852e`，
CLI 包 dbt-metricflow 为 `0.15.0.dev0`，引擎库 metricflow 为 `0.213.0.dev0`。
模型已改用 DuckDB 的 `tpcds.main` 和 DuckDB 日期表达式。自定义 catalog 时必须同步
原生模型及 runtime 配置。不得单独改用 PostgreSQL 或偷偷降级为 Agent SQL。
本次只验证源码版本和模型表达式，没有安装并运行完整 MetricFlow runtime。
Cube 尚无实现，不包含在本地入口的可选目标中。

## 看报告，不看哈希

打开命令末尾输出的 `runs/local-live-.../REPORT.zh-CN.md`：

- “正确”：提交答案的标准化结果哈希与本快照的冻结 Gold 一致。
- “不一致”：模型执行并提交了答案，但结果未与 Gold 匹配。
- “未评分”：准备失败、协议错误、超时或未提交答案；看错误详情。

每题展示原始问题、状态、耗时和工具调用。加 `--save-details` 后还会展示
提交 SQL、探索 SQL、总行数和最多 5 行结果预览。未暴露 SQL 的原生引擎会明确显示不可用。
完整结果不持久化；标准化 Gold 哈希足以比较，无需保留数据库连接或恢复结果行。
隐藏推理内容不采集。

摘要分别统计尝试次数、提交后参与 Gold 比对次数、正确/不一致次数、未评分次数和供应商/API 错误次数。比如 6 次中 3 次 HTTP 403、1 次未提交、2 次提交但不匹配，应该读作“2 个已提交答案不匹配，4 次未评分”，不能说“6 个分析答案全错”。`submitted_result_match_rate` 只描述提交子集；`publishable_execution_accuracy` 对探索运行始终为 null。403 需要检查网关权限/配额，本补丁不能修复供应商授权。

其他文件：`summary.json` 是机器可读摘要；`*.candidate.json` 是脱敏原生记录；
`trials/*/trial.json` 和 `trace.jsonl` 是标准评测产物。
准备阶段失败也会保留诊断，并继续其他目标。可读报告包含数据预览，只保存在本地，
不要在使用企业私有数据时公开这些文件。

## 验证与边界

```bash
python -m scripts.benchmark_lint
python -m pytest -q --basetemp ../slb-pytest-temp
```

必须把 pytest 临时目录放在仓库外，否则路径身份测试可能受环境影响。
`blank_context` 仍需通过 `db.list_relations(schema=...)` 发现表，目前没有 schema 枚举工具；
这项设计缺口保留并披露，未偷偷给对照组额外上下文。发现请求不计入执行 SQL 的次数。
正式发布报告仍要求 12 题 × 6 目标 × 3 重复 = 216 条完整记录；部分运行不绕过门禁。

## 本次补丁覆盖

已修复：提交答案筛选、OKF 目录校验/跟随、MetricFlow CLI 版本探针与 DuckDB 模型表达式、
preflight 关闭/诊断/物化、控制组 wire-format 与预览脱敏、dotenv 忽略规则、短参数生成、
可配置 live 入口、SQL/预览/正确性报告，以及工具 schema hash 在关闭前记录。
本次再次修订补齐 representative 公开输出契约与 SQL/lint/Gold 对照校验，保持严格评分，并拆分供应商失败与已提交答案正确性。

未声称完成：Cube、完整 MetricFlow runtime 安装、macOS 实机验证、全 99 题结果验证、
真实模型重复运行与正式发布、schema 枚举设计及 OpenTelemetry Collector 导出。
