from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping
from urllib.parse import unquote, urlparse

import duckdb
import yaml


@dataclass(frozen=True)
class DatabaseSettings:
    driver: str
    url: str
    catalog: str | None
    schema: str
    read_only: bool


@dataclass(frozen=True)
class QueryResult:
    columns: tuple[str, ...]
    rows: list[tuple[Any, ...]]
    elapsed_ms: float


def _env_or_default(spec: Mapping[str, Any]) -> Any:
    value = os.getenv(str(spec["env"]))
    return value if value not in (None, "") else spec.get("default")


def load_database_settings(path: str | Path = "runner/config/database.yaml") -> DatabaseSettings:
    document = yaml.safe_load(Path(path).read_text())
    connection = document["connection"]
    namespace = document["namespace"]
    return DatabaseSettings(
        driver=str(connection["driver"]),
        url=str(_env_or_default(connection["url"])),
        catalog=_env_or_default(namespace["catalog"]),
        schema=str(_env_or_default(namespace["schema"])),
        read_only=bool(connection.get("read_only", True)),
    )


def duckdb_path_from_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "duckdb":
        raise ValueError(f"Unsupported database URL scheme: {parsed.scheme!r}")
    if parsed.netloc not in ("", None):
        raise ValueError("DuckDB URLs must not contain a host")
    path = unquote(parsed.path)
    if path in ("/:memory:", ":memory:"):
        return ":memory:"
    if path.startswith("/./"):
        return path[3:]
    if not path:
        raise ValueError("DuckDB URL must include a database path")
    return path


class DuckDBAdapter:
    def __init__(self, settings: DatabaseSettings):
        if settings.driver != "duckdb":
            raise ValueError(f"DuckDBAdapter cannot use driver {settings.driver!r}")
        self.settings = settings
        self.connection: duckdb.DuckDBPyConnection | None = None

    def __enter__(self) -> "DuckDBAdapter":
        path = duckdb_path_from_url(self.settings.url)
        self.connection = duckdb.connect(path, read_only=self.settings.read_only)
        self.connection.execute(f'SET schema = "{self.settings.schema.replace(chr(34), chr(34) * 2)}"')
        return self

    def __exit__(self, *_: object) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def execute(self, sql: str, parameters: tuple[Any, ...] = ()) -> QueryResult:
        if self.connection is None:
            raise RuntimeError("Database adapter is not connected")
        started = perf_counter()
        cursor = self.connection.execute(sql, parameters)
        rows = cursor.fetchall()
        elapsed_ms = (perf_counter() - started) * 1000
        columns = tuple(item[0] for item in (cursor.description or ()))
        return QueryResult(columns=columns, rows=rows, elapsed_ms=elapsed_ms)


def connect(settings: DatabaseSettings | None = None) -> DuckDBAdapter:
    resolved = settings or load_database_settings()
    if resolved.driver == "duckdb":
        return DuckDBAdapter(resolved)
    raise ValueError(f"No adapter registered for driver {resolved.driver!r}")

