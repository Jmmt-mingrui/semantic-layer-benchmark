# 实例化问题

本目录连接符号化 Canonical Question 和可执行 Agent Trial。Qualification 使用 [`question-instance.schema.json`](../../../../runner/contracts/question-instance.schema.json) v0.1.0；12 道代表题使用 [`representative-question-instance.schema.json`](../../../../runner/contracts/representative-question-instance.schema.json) v0.3.0。

记录按照信任边界分区：

- `target_input` 只包含完全渲染的问题，是 Runner 构建用户消息时唯一可以读取的区域。
- `orchestrator_only` 保存用于复现的强类型实例化参数，但永远不会发送给 Agent。
- `evaluator_only` 包含参考 SQL 路径、预期语句数、结果比较方式和出处，只能在目标 Sandbox 关闭后加载。

q01 Qualification Instance 是第一个经过 Review 的 Pilot；12 道代表题已按同一来源链实例化。全部 99 题运行前，其余问题仍需实例化。包含 `<PLACEHOLDER>` 的问题无效。q14、q23、q24 和 q39 可以声明两条参考语句，其他问题只能声明一条。

实例化问题必须明确写出影响结果一致性的输出要求，包括选择字段、分组、排序、Limit 和是否预期多个输出。这样可以避免 Evaluator 要求 Agent 从未被告知的行为。

这些文件可以包含固定的公开 Qualification 参数，但绝不能包含预期结果行、结果 Hash、凭据或隐藏提示。

## 公开输出契约迁移

`public-output-contract-v1` 将欠定义的 representative v0.2.0 记录迁移到 v0.3.0，并更换实例 ID。参数改用 qualification 的 name/type/value 强类型数组。单语句的 `evaluator_only.result_contract` 包含 `columns`、`order_sensitive`、`max_rows`、`comparison`、`order_by`；q14/q39 的 `result_contract.statements` 按提交顺序包含两个同样结构的契约。`max_rows: null` 表示不限条数。评分仍是顺序敏感的 `exact_normalized` / `canonical-json-v1`，没有按名重排列、重排行、去重或新增数值容差。

公开要求在实例化时写入 `target_input.question`；Runner 仍只发送这一个字符串。q01 两个版本题干完全一致。[可审阅定义](../../../../scripts/materialize_representative_questions.py) 写清原 SQL 的日期端点、q02 比值方向/日期配对重复行、q49 升序排名、q75 明细去重和 q84 人口属性键关联。Schema/lint 校验全部 14 条语句的绑定列、**最外层** ORDER BY/LIMIT；只有隐藏元数据声明要求、题面未告知时会被拒绝。

q02/q14/q39 新增输出别名，q36/q75 新增确定性的最终排序 tie-break。这是已声明的展示修订，不改变分组、过滤、比值、排名或重复行语义，见 [SQL 修订说明](../../sql/reference/duckdb/SOURCE.md)。旧 Gold 和成绩不能与新题面互换。运行前须在同一份已校验 SF1 快照上重新冻结 Gold；实例和 SQL Hash 会拒绝旧包。单元/空 Schema 覆盖不代表新一轮真实模型 SF1 测试完成。

```bash
python -m scripts.materialize_representative_questions
python -m scripts.benchmark_lint --check question-output-contracts
python -m scripts.freeze_representative_sf1
python -m scripts.freeze_representative_sf1 --verify
```

实例化工具默认检查漂移；`--patch` 仅打印适用于 apply_patch 的更新，不写文件、不读取 Gold 结果。
