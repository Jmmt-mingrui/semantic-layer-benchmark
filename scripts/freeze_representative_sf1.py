from __future__ import annotations

import argparse
import json

from runner.core.representative_gold import freeze_representative_pack, verify_representative_pack


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze or verify the 12-question TPC-DS-derived SF1 representative Gold pack"
    )
    parser.add_argument("--manifest", default="data/tpcds/sf1/manifests/duckdb-sf1.json")
    parser.add_argument("--instances", default="benchmark/tpcds/questions/instances/sf1-representative-v1.jsonl")
    parser.add_argument("--output-dir", default="benchmark/tpcds/results/gold/sf1/representative-v1")
    parser.add_argument("--root", default=".")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument(
        "--development",
        action="store_true",
        help="Permit external/local paths for development only; never publish artifacts produced this way",
    )
    parser.add_argument(
        "--skip-source-rehash",
        action="store_true",
        help="Do not rehash generated .dat inputs. Publication freeze should not use this flag.",
    )
    args = parser.parse_args()
    publication = not args.development
    require_sources = not args.skip_source_rehash

    if args.verify:
        report = verify_representative_pack(
            pack_path=f"{args.output_dir}/pack.json",
            root=args.root,
            publication=publication,
            require_sources=require_sources,
        )
    else:
        report = freeze_representative_pack(
            manifest_path=args.manifest,
            instances_path=args.instances,
            output_dir=args.output_dir,
            root=args.root,
            publication=publication,
            require_sources=require_sources,
        )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
