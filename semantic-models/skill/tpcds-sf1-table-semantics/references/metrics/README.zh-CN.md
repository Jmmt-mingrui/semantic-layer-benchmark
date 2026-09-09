# 业务指标索引

遇到聚合、比率、同期比较、排名或 KPI 问题时，先读取 `index.md`，再按需加载基础指标、派生指标、query-exact 指标和 99 题映射。

指标 ID、公式与渠道 variant 必须与 `semantic-models/canonical/tpcds-sf1/` 保持一致。`analysis_operations` 是查询操作，不应被误定义成指标；query-exact 公式是 TPC-DS 特定公式，不能擅自替换成更常见的业务口径。

