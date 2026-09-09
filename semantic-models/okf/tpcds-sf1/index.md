---
okf_version: "0.2"
---

# TPC-DS SF1 semantic knowledge bundle

This OKF bundle describes the 24 business tables and the candidate canonical business metrics in the benchmark's TPC-DS-derived PostgreSQL SF1 schema.

## Contents

* [Tables](tables/) - Table grain, columns, semantic roles, joins, and query guidance.
* [Business metrics](metrics/) - 42 base metric families, 25 derived metrics, 9 query-exact formulas, and mappings for all 99 questions.

## Trust and scope

All table and metric concepts are `draft` until independently reviewed. They describe a TPC-DS-derived workload, not an audited TPC benchmark implementation. Metric formulas follow the canonical source precedence: official toolkit template, then pinned reference SQL, then question paraphrase.
