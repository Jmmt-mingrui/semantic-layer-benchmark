# Evaluator-only SF1 Gold identities

[English](README.md) | [简体中文](README.zh-CN.md)

This directory stores result identities, never raw result rows. Targets must never mount or read this directory. Gold is loaded only by evaluator code after the target/provider conversation has closed.

The publication target is `representative-v1/`, containing one question-level Gold artifact for each of q01, q02, q03, q05, q12, q14, q21, q36, q39, q49, q75, and q84 plus a pack manifest. q14 and q39 each bind two required reference statements inside one question artifact so they still contribute one question-level denominator.

Every frozen artifact binds the exact TPC-DS-derived SF1 dataset manifest and database identity, the selected question-instance line hash, every reference SQL SHA-256, result columns, row count, and normalized result SHA-256. Changing any input makes `--verify` fail closed.

The representative Gold files are intentionally absent from source control until an official TPC-DS v4.0.0 `dsdgen` binary and all generated SF1 inputs are available locally and pass publication preflight. Generate and verify them with:

```bash
python -m scripts.freeze_representative_sf1
python -m scripts.freeze_representative_sf1 --verify
```

Development mode exists only for tests/local diagnosis and must not be published as a benchmark result. The legacy q01-only freeze command remains for compatibility.
