from __future__ import annotations

import json

import pytest

from runner.adapters.cube.rest_adapter import (
    CubeRestAdapter,
    CubeRestConfig,
    CubeTransportResponse,
)
from runner.core.native_adapter import (
    NativeAdapterError,
    NativeIsolationError,
    NativeOperationError,
    NativeRequest,
)


class FakeTransport:
    def __init__(self, responses: dict[str, CubeTransportResponse | Exception]) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    def request(self, *, method: str, url: str, headers: object, timeout_seconds: float) -> CubeTransportResponse:
        self.calls.append(
            {"method": method, "url": url, "headers": headers, "timeout_seconds": timeout_seconds}
        )
        result = self.responses[url]
        if isinstance(result, Exception):
            raise result
        return result


def response(status: int, body: dict[str, object]) -> CubeTransportResponse:
    return CubeTransportResponse(status, {"content-type": "application/json"}, json.dumps(body).encode())


def config(**overrides: object) -> CubeRestConfig:
    values: dict[str, object] = {
        "base_url": "https://cube.example.test",
        "image_digest": "sha256:" + "a" * 64,
        "runtime_identity": "cubejs-server:0.35.0",
        "api_token": "super-secret-token",
    }
    values.update(overrides)
    return CubeRestConfig(**values)


def test_preflight_uses_only_native_readyz_and_meta_and_sanitizes_artifacts() -> None:
    base = "https://cube.example.test/cubejs-api/v1"
    transport = FakeTransport(
        {
            "https://cube.example.test/readyz": response(200, {"status": "ok"}),
            base + "/meta": response(200, {"cubes": [{"name": "StoreSales"}]}),
        }
    )
    adapter = CubeRestAdapter(config(), transport=transport)

    readyz, meta = adapter.preflight(12)

    assert [call["url"] for call in transport.calls] == ["https://cube.example.test/readyz", base + "/meta"]
    assert readyz.status == meta.status == "ok"
    assert "super-secret-token" not in readyz.request_artifact
    assert "StoreSales" not in meta.response_artifact
    assert '"cubes"' in meta.response_artifact
    assert transport.calls[0]["headers"] == {
        "Accept": "application/json",
        "Authorization": "super-secret-token",
    }


def test_load_encodes_rest_query_without_sql_or_database_fallback() -> None:
    base = "https://cube.example.test/cubejs-api/v1"
    query = {"measures": ["StoreSales.totalSales"], "limit": 1}
    transport = FakeTransport({})
    adapter = CubeRestAdapter(config(), transport=transport)

    encoded_url = base + "/load?query=%7B%22limit%22%3A1%2C%22measures%22%3A%5B%22StoreSales.totalSales%22%5D%7D"
    transport.responses[encoded_url] = response(200, {"data": [{"StoreSales.totalSales": "42"}]})
    result = adapter.dispatch(NativeRequest("cube.load", {"query": query}, 99))

    assert result.status == "ok"
    assert result.output["payload"]["data"][0]["StoreSales.totalSales"] == "42"
    assert transport.calls[0]["url"] == encoded_url
    assert transport.calls[0]["timeout_seconds"] == 30.0
    assert "cube.sql" not in [tool["name"] for tool in adapter.public_tools()]


def test_sql_and_undeclared_operations_are_rejected_before_transport() -> None:
    adapter = CubeRestAdapter(config(), transport=FakeTransport({}))

    with pytest.raises(NativeIsolationError, match="Prohibited"):
        adapter.dispatch(NativeRequest("cube.sql", {}, 1))
    with pytest.raises(NativeOperationError, match="SQL payloads"):
        adapter.dispatch(NativeRequest("cube.load", {"query": {"sql": "select 1"}}, 1))
    with pytest.raises(NativeIsolationError, match="Prohibited"):
        adapter.dispatch(NativeRequest("db.execute_readonly", {}, 1))


def test_timeout_and_missing_native_surface_never_fallback() -> None:
    base = "https://cube.example.test/cubejs-api/v1"
    timeout_transport = FakeTransport({base + "/meta": TimeoutError()})
    timeout = CubeRestAdapter(config(), transport=timeout_transport).dispatch(NativeRequest("cube.meta", {}, 2))
    assert timeout.status == "timeout"
    assert len(timeout_transport.calls) == 1

    unavailable_transport = FakeTransport({base + "/meta": response(404, {"error": "not found"})})
    unavailable = CubeRestAdapter(config(), transport=unavailable_transport).dispatch(NativeRequest("cube.meta", {}, 2))
    assert unavailable.status == "unsupported"
    assert len(unavailable_transport.calls) == 1


def test_runtime_identity_must_be_pinned_and_adapter_cannot_reopen() -> None:
    with pytest.raises(NativeAdapterError, match="image_digest"):
        CubeRestAdapter(config(image_digest="cube:latest"))
    with pytest.raises(NativeAdapterError, match="runtime_identity"):
        CubeRestAdapter(config(runtime_identity=" "))

    adapter = CubeRestAdapter(config(), transport=FakeTransport({}))
    adapter.close()
    with pytest.raises(NativeAdapterError, match="closed"):
        adapter.preflight(1)
