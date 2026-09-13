"""Closed adapter for Cube's REST Query API.

The adapter intentionally supports only Cube's ``/readyz``, ``/meta`` and
``/load`` surfaces. It does not call Cube SQL APIs and it cannot fall back to
DuckDB or another database when Cube is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
import time
from typing import Any, Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from runner.core.native_adapter import (
    NativeAdapterError,
    NativeOperationError,
    NativeRequest,
    NativeResponse,
    assert_declared_operation,
)


_IMAGE_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_CUBE_TARGET = {
    "allowed_operations": {"cube.meta", "cube.load"},
    "prohibited_operations": {
        "cube.sql",
        "db.list_relations",
        "db.describe_relations",
        "db.execute_readonly",
        "benchmark.read_gold",
    },
}
_PRELIGHT_OPERATIONS = {"cube.readyz", "cube.meta"}
_SQL_KEYS = frozenset({"sql", "sqlquery", "sql_query", "sqlapi"})


@dataclass(frozen=True)
class CubeRestConfig:
    """Pinned runtime identity and immutable REST endpoint settings.

    ``runtime_identity`` is a human-readable Cube release/build identifier. It
    complements, rather than replaces, the immutable image digest. No identity
    is inferred from a live response, because that would make a run ambiguous.
    """

    base_url: str
    image_digest: str
    runtime_identity: str
    api_token: str | None = None
    api_base_path: str = "/cubejs-api/v1"
    maximum_timeout_seconds: float = 30.0

    def validate(self) -> None:
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise NativeAdapterError("Cube base_url must be an absolute HTTP(S) URL")
        if parsed.query or parsed.fragment:
            raise NativeAdapterError("Cube base_url must not contain a query or fragment")
        if not _IMAGE_DIGEST.fullmatch(self.image_digest):
            raise NativeAdapterError("Cube image_digest must be a lowercase sha256 digest")
        if not self.runtime_identity.strip():
            raise NativeAdapterError("Cube runtime_identity is required")
        if not self.api_base_path.startswith("/") or self.api_base_path.rstrip("/") != self.api_base_path:
            raise NativeAdapterError("Cube api_base_path must start with / and omit a trailing /")
        if self.maximum_timeout_seconds <= 0:
            raise NativeAdapterError("Cube maximum_timeout_seconds must be positive")


@dataclass(frozen=True)
class CubeTransportResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes


class CubeHttpTransport(Protocol):
    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> CubeTransportResponse: ...


class UrllibCubeTransport:
    """Small stdlib transport; tests inject a deterministic fake instead."""

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> CubeTransportResponse:
        request = Request(url, method=method, headers=dict(headers))
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310: configured Cube endpoint
                return CubeTransportResponse(
                    status_code=response.status,
                    headers=dict(response.headers.items()),
                    body=response.read(),
                )
        except HTTPError as error:
            return CubeTransportResponse(
                status_code=error.code,
                headers=dict(error.headers.items()) if error.headers else {},
                body=error.read(),
            )
        except TimeoutError:
            raise
        except URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise TimeoutError from error
            raise NativeAdapterError("Cube REST transport failed") from error


class CubeRestAdapter:
    """A target-specific adapter for the non-SQL Cube REST Query API."""

    version = "cube-rest-adapter-v1"

    def __init__(
        self,
        config: CubeRestConfig,
        *,
        transport: CubeHttpTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        config.validate()
        self._config = config
        self._transport = transport or UrllibCubeTransport()
        self._clock = clock
        self._closed = False

    def preflight(self, deadline_seconds: float) -> tuple[NativeResponse, NativeResponse]:
        """Check Cube readiness and discover its native metadata before a trial."""

        self._assert_open()
        return (
            self._invoke_preflight("cube.readyz", deadline_seconds),
            self._invoke_preflight("cube.meta", deadline_seconds),
        )

    def public_tools(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Only agent-visible operations from the target registry are returned."""

        return (
            {
                "name": "cube.meta",
                "description": "Inspect Cube's native REST metadata.",
                "input_schema": {"type": "object", "additionalProperties": False},
            },
            {
                "name": "cube.load",
                "description": "Run a native Cube REST Query API load request.",
                "input_schema": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {"query": {"type": "object"}},
                    "additionalProperties": False,
                },
            },
        )

    def dispatch(self, request: NativeRequest) -> NativeResponse:
        self._assert_open()
        assert_declared_operation(_CUBE_TARGET, request.operation)
        timeout = self._effective_timeout(request.deadline_seconds)
        if request.operation == "cube.meta":
            if request.arguments:
                raise NativeOperationError("cube.meta does not accept arguments")
            return self._request("cube.meta", "/meta", timeout)
        if request.operation == "cube.load":
            query = self._validate_load_arguments(request.arguments)
            encoded_query = json.dumps(query, sort_keys=True, separators=(",", ":"))
            return self._request(
                "cube.load",
                "/load?" + urlencode({"query": encoded_query}),
                timeout,
            )
        raise NativeOperationError(f"Unsupported Cube operation: {request.operation}")

    def close(self) -> None:
        self._closed = True

    def _invoke_preflight(self, operation: str, deadline_seconds: float) -> NativeResponse:
        if operation not in _PRELIGHT_OPERATIONS:
            raise NativeOperationError(f"Undeclared Cube preflight operation: {operation}")
        timeout = self._effective_timeout(deadline_seconds)
        return self._request(
            operation,
            "/readyz" if operation == "cube.readyz" else "/meta",
            timeout,
            api_surface=operation != "cube.readyz",
        )

    def _request(
        self,
        operation: str,
        path: str,
        timeout_seconds: float,
        *,
        api_surface: bool = True,
    ) -> NativeResponse:
        started = self._clock()
        url = self._build_url(path, api_surface=api_surface)
        request_artifact = json.dumps(
            {"method": "GET", "operation": operation, "path": path},
            sort_keys=True,
            separators=(",", ":"),
        )
        try:
            response = self._transport.request(
                method="GET",
                url=url,
                headers=self._headers(),
                timeout_seconds=timeout_seconds,
            )
        except TimeoutError:
            return self._response("timeout", started, {"error": "timeout"}, request_artifact)
        except Exception as error:  # transport implementations are untrusted boundaries
            return self._response(
                "error",
                started,
                {"error": "transport_error", "exception_type": type(error).__name__},
                request_artifact,
            )

        response_artifact = self._response_artifact(response)
        if response.status_code in {404, 405, 501}:
            return self._response(
                "unsupported",
                started,
                {"error": "native_surface_unavailable", "http_status": response.status_code},
                request_artifact,
                response_artifact,
            )
        if not 200 <= response.status_code < 300:
            return self._response(
                "error",
                started,
                {"error": "native_http_error", "http_status": response.status_code},
                request_artifact,
                response_artifact,
            )
        try:
            payload = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._response(
                "error",
                started,
                {"error": "invalid_native_json"},
                request_artifact,
                response_artifact,
            )
        if not isinstance(payload, dict):
            return self._response(
                "error",
                started,
                {"error": "invalid_native_payload"},
                request_artifact,
                response_artifact,
            )
        return self._response(
            "ok",
            started,
            {"payload": payload},
            request_artifact,
            response_artifact,
        )

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._config.api_token:
            headers["Authorization"] = self._config.api_token
        return headers

    def _build_url(self, suffix: str, *, api_surface: bool) -> str:
        base = self._config.base_url.rstrip("/")
        return base + (self._config.api_base_path if api_surface else "") + suffix

    def _effective_timeout(self, deadline_seconds: float) -> float:
        if deadline_seconds <= 0:
            raise NativeAdapterError("Cube operation deadline_seconds must be positive")
        return min(deadline_seconds, self._config.maximum_timeout_seconds)

    def _assert_open(self) -> None:
        if self._closed:
            raise NativeAdapterError("Cube REST adapter is closed")

    @staticmethod
    def _validate_load_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
        if set(arguments) != {"query"} or not isinstance(arguments["query"], dict):
            raise NativeOperationError("cube.load requires exactly one object argument: query")
        query = arguments["query"]
        if CubeRestAdapter._contains_sql_key(query):
            raise NativeOperationError("cube.load accepts REST query objects, not SQL payloads")
        return query

    @staticmethod
    def _contains_sql_key(value: Any) -> bool:
        if isinstance(value, dict):
            return any(
                str(key).replace("-", "").replace("_", "").lower() in _SQL_KEYS
                or CubeRestAdapter._contains_sql_key(item)
                for key, item in value.items()
            )
        if isinstance(value, list):
            return any(CubeRestAdapter._contains_sql_key(item) for item in value)
        return False

    def _response(
        self,
        status: str,
        started: float,
        output: dict[str, Any],
        request_artifact: str,
        response_artifact: str | None = None,
    ) -> NativeResponse:
        return NativeResponse(
            status=status,
            duration_ms=max(0.0, (self._clock() - started) * 1000),
            output=output,
            request_artifact=request_artifact,
            response_artifact=response_artifact,
        )

    @staticmethod
    def _response_artifact(response: CubeTransportResponse) -> str:
        """Persist only a structural response summary, never credentials or rows."""

        try:
            decoded = json.loads(response.body.decode("utf-8"))
            payload_keys = sorted(decoded) if isinstance(decoded, dict) else []
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload_keys = []
        return json.dumps(
            {
                "content_type": response.headers.get("content-type", ""),
                "http_status": response.status_code,
                "payload_keys": payload_keys,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
