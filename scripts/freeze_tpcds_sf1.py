from __future__ import annotations

import argparse
import json

from runner.core.dataset import freeze_gold_result, validate_sf1_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a generated TPC-DS-derived SF1 snapshot and freeze a q01 gold-result identity"
    )
    parser.add_argument("--manifest", default="data/tpcds/sf1/manifests/duckdb-sf1.json")
    parser.add_argument(
        "--questions",
        default="benchmark/tpcds/questions/instances/sf1-qualification-q01.jsonl",
    )
    parser.add_argument("--question-id", default="q01", choices=("q01",))
    parser.add_argument("--output", default="benchmark/tpcds/results/gold/sf1/q01.json")
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--development",
        action="store_true",
        help="Allow a missing dsdgen binary hash and absolute local paths; never publish this mode",
    )
    parser.add_argument(
        "--require-sources",
        action="store_true",
        help="Rehash all 25 generated .dat inputs in addition to the loaded database",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run all snapshot checks without writing a gold-result artifact",
    )
    args = parser.parse_args()
    publication = not args.development
    if args.validate_only:
        report = validate_sf1_snapshot(
            args.manifest,
            root=args.root,
            publication=publication,
            require_sources=args.require_sources,
        )
        print(
            json.dumps(
                {
                    "manifest_sha256": report["manifest_sha256"],
                    "dataset_sha256": report["dataset_sha256"],
                    "database_sha256": report["database_sha256"],
                    "table_count": report["table_count"],
                    "total_rows": report["total_rows"],
                },
                sort_keys=True,
            )
        )
        return
    artifact = freeze_gold_result(
        args.manifest,
        args.questions,
        args.output,
        question_id=args.question_id,
        root=args.root,
        publication=publication,
        require_sources=args.require_sources,
    )
    print(
        json.dumps(
            {
                "question_id": artifact["question_id"],
                "dataset_sha256": artifact["dataset"]["dataset_sha256"],
                "result_sha256": artifact["result"]["sha256"],
                "row_count": artifact["result"]["row_count"],
                "output": args.output,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
