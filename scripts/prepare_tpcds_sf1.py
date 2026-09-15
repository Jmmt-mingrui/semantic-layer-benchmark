"""Run the publishable TPC-DS-derived SF1 preparation pipeline.

The TPC toolkit is intentionally not downloaded by this command. TPC requires
each user to accept its licence and register before downloading the tools, so a
caller must supply the official v4.0.0 ``dsdgen`` binary explicitly.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Sequence


DEFAULT_MANIFEST = Path("data/tpcds/sf1/manifests/duckdb-sf1.json")
DEFAULT_GOLD_DIR = Path("benchmark/tpcds/results/gold/sf1/representative-v1")


def checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: Sequence[str], *, root: Path) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=root, check=True)


def require_repository_root(root: Path) -> None:
    required = (
        root / "pyproject.toml",
        root / "data/tpcds/schema/duckdb/schema.sql",
        root / "benchmark/tpcds/questions/instances/sf1-representative-v1.jsonl",
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Not a benchmark repository root; missing: " + ", ".join(missing))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate, load, freeze, and verify the publishable TPC-DS-derived SF1 baseline"
    )
    parser.add_argument(
        "--dsdgen",
        type=Path,
        required=True,
        help="Official TPC-DS Tools v4.0.0 dsdgen binary obtained under the TPC licence",
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing generated .dat files, DuckDB database, and Gold identities",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip repository lint and pytest after the SF1 and Gold verification gates",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    require_repository_root(root)
    binary = args.dsdgen.resolve()
    if not binary.is_file():
        raise FileNotFoundError(f"dsdgen binary not found: {binary}")
    if not binary.stat().st_mode & 0o111:
        raise PermissionError(f"dsdgen is not executable: {binary}")

    python = sys.executable
    overwrite = ["--overwrite"] if args.overwrite else []
    run(
        [python, "-m", "scripts.generate_tpcds_sf1", "--dsdgen", str(binary), *overwrite],
        root=root,
    )
    run(
        [
            python,
            "-m",
            "scripts.load_tpcds_sf1",
            "--generator-version",
            "4.0.0",
            "--generator-binary",
            str(binary),
            *overwrite,
        ],
        root=root,
    )
    run([python, "-m", "scripts.freeze_representative_sf1"], root=root)
    run([python, "-m", "scripts.freeze_representative_sf1", "--verify"], root=root)
    if not args.skip_tests:
        run([python, "-m", "scripts.benchmark_lint"], root=root)
        # Keep pytest's generated fixtures outside the repository. Some managed
        # environments redirect the system temporary directory into the current
        # checkout, which changes the evaluator's path-identity semantics and
        # also makes repository-wide validators inspect transient JSONL files.
        with tempfile.TemporaryDirectory(
            prefix="semantic-benchmark-pytest-", dir=root.parent
        ) as test_directory:
            run([python, "-m", "pytest", "-q", "--basetemp", test_directory], root=root)

    manifest = json.loads((root / DEFAULT_MANIFEST).read_text(encoding="utf-8"))
    pack = json.loads((root / DEFAULT_GOLD_DIR / "pack.json").read_text(encoding="utf-8"))
    summary = {
        "status": "ready",
        "benchmark": "TPC-DS-derived",
        "scale_factor": 1,
        "dsdgen_sha256": checksum(binary),
        "dataset_sha256": manifest["dataset_sha256"],
        "database_sha256": manifest["database"]["sha256"],
        "table_count": len(manifest["tables"]),
        "total_rows": sum(int(table["rows"]) for table in manifest["tables"].values()),
        "gold_question_count": pack["question_count"],
        "gold_statement_count": pack["statement_count"],
        "gold_pack_identity_sha256": pack["pack_identity_sha256"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
