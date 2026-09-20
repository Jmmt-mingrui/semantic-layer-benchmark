"""Fast, secret-safe diagnostics for a benchmark checkout.

The publishable benchmark intentionally cannot bundle licensed TPC-DS data or
provider credentials.  This command separates a broken Python installation
from those expected, user-supplied runtime prerequisites.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse

import duckdb
import yaml


REQUIRED_REPOSITORY_FILES = (
    "pyproject.toml",
    "runner/config/database.yaml",
    "runner/config/targets.native.yaml",
    "runner/tools/blank-context.tools.json",
    "benchmark/tpcds/questions/instances/sf1-representative-v1.jsonl",
    "data/tpcds/schema/duckdb/schema.sql",
)
TPCDS_TABLE_COUNT = 25


def _check(name: str, status: str, detail: str, *, required: bool) -> dict[str, Any]:
    return {"name": name, "status": status, "required": required, "detail": detail}


def _database_path(root: Path) -> Path | None:
    config_path = root / "runner/config/database.yaml"
    if not config_path.is_file():
        return None
    document = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    raw = os.getenv("BENCHMARK_DATABASE_URL")
    if not raw:
        raw = document.get("connection", {}).get("url", {}).get("default")
    prefix = "duckdb:///"
    if not isinstance(raw, str) or not raw.startswith(prefix):
        return None
    path = Path(raw[len(prefix):])
    return path if path.is_absolute() else (root / path).resolve()


def diagnose(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    checks: list[dict[str, Any]] = []

    python_ok = sys.version_info >= (3, 11)
    checks.append(
        _check(
            "python",
            "ok" if python_ok else "error",
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            required=True,
        )
    )

    try:
        connection = duckdb.connect(":memory:")
        try:
            answer = connection.execute("select 42").fetchone()
        finally:
            connection.close()
        duckdb_ok = answer == (42,)
        detail = f"{duckdb.__version__}; in-memory query returned {answer!r}"
    except Exception as error:  # pragma: no cover - protects the diagnostic itself
        duckdb_ok = False
        detail = f"{type(error).__name__}: {error}"
    checks.append(_check("duckdb", "ok" if duckdb_ok else "error", detail, required=True))

    missing = [path for path in REQUIRED_REPOSITORY_FILES if not (root / path).is_file()]
    checks.append(
        _check(
            "repository",
            "ok" if not missing else "error",
            str(root) if not missing else "missing: " + ", ".join(missing),
            required=True,
        )
    )

    database_path = _database_path(root)
    database_ready = False
    if database_path is not None and database_path.is_file():
        try:
            connection = duckdb.connect(str(database_path), read_only=True)
            try:
                table_count = connection.execute(
                    "select count(*) from information_schema.tables "
                    "where table_schema = 'main' and table_type = 'BASE TABLE'"
                ).fetchone()[0]
            finally:
                connection.close()
            database_ready = table_count == TPCDS_TABLE_COUNT
            database_detail = f"{database_path}; {table_count} main tables"
            if not database_ready:
                database_detail += f" (expected {TPCDS_TABLE_COUNT})"
        except Exception as error:
            database_detail = f"{database_path}; {type(error).__name__}: {error}"
    else:
        database_detail = "run: python -m scripts.prepare_tpcds_sf1 --dsdgen /path/to/dsdgen"
    checks.append(
        _check(
            "sf1_database",
            "ok" if database_ready else "error" if database_path and database_path.exists() else "missing",
            database_detail,
            required=False,
        )
    )

    manifest_path = root / "data/tpcds/sf1/manifests/duckdb-sf1.json"
    manifest_ready = False
    manifest_detail = "created by the SF1 preparation pipeline"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_ready = (
                isinstance(manifest.get("dataset_sha256"), str)
                and len(manifest.get("tables", {})) == TPCDS_TABLE_COUNT
            )
            manifest_detail = str(manifest_path)
            if not manifest_ready:
                manifest_detail += "; missing dataset identity or complete table inventory"
        except (OSError, json.JSONDecodeError) as error:
            manifest_detail = f"{manifest_path}; {type(error).__name__}: {error}"
    checks.append(
        _check(
            "sf1_manifest",
            "ok" if manifest_ready else "error" if manifest_path.exists() else "missing",
            manifest_detail,
            required=False,
        )
    )

    gold_path = root / "benchmark/tpcds/results/gold/sf1/representative-v1/pack.json"
    gold_ready = False
    gold_detail = "created by the SF1 preparation pipeline"
    if gold_path.is_file():
        try:
            gold = json.loads(gold_path.read_text(encoding="utf-8"))
            gold_ready = (
                gold.get("question_count") == 12
                and isinstance(gold.get("pack_identity_sha256"), str)
                and len(gold.get("gold", [])) == 12
            )
            gold_detail = str(gold_path)
            if not gold_ready:
                gold_detail += "; incomplete representative-v1 identity"
        except (OSError, json.JSONDecodeError) as error:
            gold_detail = f"{gold_path}; {type(error).__name__}: {error}"
    checks.append(
        _check(
            "gold_pack",
            "ok" if gold_ready else "error" if gold_path.exists() else "missing",
            gold_detail,
            required=False,
        )
    )

    provider_values = {
        "BENCHMARK_AGENT_PROVIDER": os.getenv("BENCHMARK_AGENT_PROVIDER"),
        "BENCHMARK_AGENT_MODEL": os.getenv("BENCHMARK_AGENT_MODEL"),
        "BENCHMARK_AGENT_ENDPOINT": os.getenv("BENCHMARK_AGENT_ENDPOINT"),
    }
    missing_provider = [name for name, value in provider_values.items() if not value]
    endpoint = provider_values["BENCHMARK_AGENT_ENDPOINT"]
    endpoint_ok = not endpoint or (
        urlparse(endpoint).scheme in {"http", "https"} and bool(urlparse(endpoint).hostname)
    )
    credential_name = os.getenv("BENCHMARK_AGENT_API_KEY_ENV")
    credential_ok = not credential_name or bool(os.getenv(credential_name))
    provider_ready = not missing_provider and endpoint_ok and credential_ok
    if provider_ready:
        provider_detail = f"{provider_values['BENCHMARK_AGENT_PROVIDER']} / {provider_values['BENCHMARK_AGENT_MODEL']}"
    elif missing_provider:
        provider_detail = "missing: " + ", ".join(missing_provider)
    elif not endpoint_ok:
        provider_detail = "BENCHMARK_AGENT_ENDPOINT must be an absolute http(s) URL"
    else:
        provider_detail = f"credential variable is empty: {credential_name}"
    checks.append(_check("live_provider", "ok" if provider_ready else "missing", provider_detail, required=False))

    installation_ready = all(check["status"] == "ok" for check in checks if check["required"])
    runtime_ready = installation_ready and all(check["status"] == "ok" for check in checks)
    return {
        "status": "ready" if runtime_ready else "installation_ok" if installation_ready else "broken",
        "installation_ready": installation_ready,
        "live_run_ready": runtime_ready,
        "checks": checks,
    }


def run_doctor(args: Any) -> int:
    root = args.root.resolve()
    if args.env_file:
        # Keep one parser and one precedence rule for doctor and run-live.
        from runner.core.local_live import load_env_file

        load_env_file((root / args.env_file).resolve())
    report = diagnose(root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["installation_ready"]:
        return 2
    if args.strict and not report["live_run_ready"]:
        return 2
    return 0
