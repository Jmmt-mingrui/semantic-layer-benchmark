"""MetricFlow CLI adapter that captures native query output as a typed result.

MetricFlow remains the sole query engine for this target.  The adapter asks the
pinned ``mf query`` command to write its own CSV output, parses that local output
without querying the benchmark database, and returns a structured native result
for the shared harness to register.  This is not a SQL fallback.
"""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Mapping

from runner.adapters.metricflow import MetricFlowAdapter
from runner.core.control_tools import result_sha256
from runner.core.database import QueryResult
from runner.core.native_adapter import NativeResponse

_INTEGER = re.compile(r"^[+-]?(?:0|[1-9][0-9]*)$")
_DECIMAL = re.compile(r"^[+-]?(?:[0-9]+\.[0-9]*|[0-9]*\.[0-9]+)$")


def _coerce_csv_value(value: str) -> Any:
    if value == "":
        return None
    if _INTEGER.fullmatch(value):
        try:
            return int(value)
        except ValueError:
            return value
    if _DECIMAL.fullmatch(value):
        try:
            return Decimal(value)
        except InvalidOperation:
            return value
    return value


def _artifact_id(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


class MetricFlowResultAdapter(MetricFlowAdapter):
    """Capture ``mf query`` CSV output for canonical trial submission."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._capture_dir = Path(tempfile.mkdtemp(prefix="semantic-layer-benchmark-mf-"))
        self._query_index = 0
        self._pending_csv: Path | None = None

    def _command_for(self, operation: str, arguments: Mapping[str, Any]) -> list[str]:
        command = super()._command_for(operation, arguments)
        if operation == "metricflow.query":
            self._query_index += 1
            self._pending_csv = self._capture_dir / f"query-{self._query_index:03d}.csv"
            command.extend(["--csv", str(self._pending_csv), "--quiet"])
        return command

    def _invoke(self, operation: str, argv: list[str], deadline_seconds: float) -> NativeResponse:
        response = super()._invoke(operation, argv, deadline_seconds)
        if operation != "metricflow.query" or response.status != "succeeded":
            return response
        path = self._pending_csv
        if path is None or not path.is_file():
            return self._local_failure(
                "metricflow.query",
                "missing_native_csv_output",
                {"detail": "MetricFlow reported success but did not produce its requested CSV output"},
            )
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
        path.unlink(missing_ok=True)
        if not rows:
            columns: list[str] = []
            values: list[list[Any]] = []
        else:
            columns = list(rows[0])
            values = [[_coerce_csv_value(cell) for cell in row] for row in rows[1:]]
            if any(len(row) != len(columns) for row in values):
                return self._local_failure("metricflow.query", "malformed_native_csv_output")

        result = QueryResult(
            columns=tuple(columns),
            rows=[tuple(row) for row in values],
            elapsed_ms=response.duration_ms,
        )
        native_result_identity = {
            "columns": columns,
            "row_count": len(values),
            "result_sha256": result_sha256(result),
        }
        output = dict(response.output)
        output["native_result"] = {"columns": columns, "rows": values}
        output["native_result_identity"] = native_result_identity
        return NativeResponse(
            status=response.status,
            duration_ms=response.duration_ms,
            output=output,
            request_artifact=response.request_artifact,
            response_artifact=_artifact_id(
                {
                    "parent_response_artifact": response.response_artifact,
                    "native_result_identity": native_result_identity,
                }
            ),
        )

    def close(self) -> None:
        try:
            super().close()
        finally:
            shutil.rmtree(self._capture_dir, ignore_errors=True)
