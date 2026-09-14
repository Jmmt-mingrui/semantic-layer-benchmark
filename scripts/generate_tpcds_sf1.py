from __future__ import annotations

import argparse
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import subprocess


TOOLKIT_VERSION = "4.0.0"


def checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate local TPC-DS-derived SF1 .dat inputs with an official TPC-DS 4.0.0 dsdgen binary"
    )
    parser.add_argument("--dsdgen", type=Path, required=True, help="Path to dsdgen built from TPC-DS Tools 4.0.0")
    parser.add_argument("--toolkit-version", default=TOOLKIT_VERSION, choices=(TOOLKIT_VERSION,))
    parser.add_argument("--output", type=Path, default=Path("data/tpcds/sf1/generated"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    binary = args.dsdgen.resolve()
    if not binary.is_file():
        raise FileNotFoundError(f"dsdgen binary not found: {binary}")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    existing = [path for path in output.glob("*.dat") if path.is_file()]
    if existing and not args.overwrite:
        raise FileExistsError("Generated .dat files already exist; pass --overwrite to replace them")
    if args.overwrite:
        for path in existing:
            path.unlink()

    command = [str(binary), "-scale", "1", "-dir", str(output), "-force"]
    completed = subprocess.run(
        command,
        cwd=binary.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "dsdgen failed with exit code "
            f"{completed.returncode}: {completed.stderr[-2000:]}"
        )

    generated = sorted(path for path in output.glob("*.dat") if path.is_file())
    if not generated:
        raise RuntimeError("dsdgen completed but produced no .dat files")
    metadata = {
        "benchmark": "TPC-DS-derived",
        "scale_factor": 1,
        "toolkit_version": args.toolkit_version,
        "generator": "dsdgen",
        "generator_binary_sha256": checksum(binary),
        "command": ["dsdgen", "-scale", "1", "-dir", "<local-output>", "-force"],
        "file_count": len(generated),
        "files": {path.name: {"sha256": checksum(path), "bytes": path.stat().st_size} for path in generated},
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "publication_note": "TPC-DS-derived SF1; not an audited or officially published TPC result.",
    }
    metadata_path = output / ".generation.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"file_count": len(generated), "generator_binary_sha256": metadata["generator_binary_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
