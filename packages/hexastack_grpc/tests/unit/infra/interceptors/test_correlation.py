from unittest.mock import AsyncMock, MagicMock

import pytest

from hexastack_core.utils.context import get_correlation_id
from hexastack_grpc.infra.interceptors.correlation import (
    AsyncCorrelationServerInterceptor,
    CorrelationServerInterceptor,
    _extract_cid,
)


def test_grpc_correlation_interceptors_instantiation() -> None:
    sync_interceptor = CorrelationServerInterceptor()
    async_interceptor = AsyncCorrelationServerInterceptor()
    assert sync_interceptor is not None
    assert async_interceptor is not None


def test_extract_cid_metadata_str_bytes_none():
    assert _extract_cid([("x-correlation-id", "corr-str")]) == "corr-str"
    assert _extract_cid([("X-CORRELATION-ID", b"corr-bytes")]) == "corr-bytes"
    fresh = _extract_cid([])
    assert isinstance(fresh, str) and len(fresh) > 0


def test_sync_correlation_interceptor_propagates():
    interceptor = CorrelationServerInterceptor()
    call_details = MagicMock()
    call_details.invocation_metadata = [("x-correlation-id", "corr-123")]

    def handler(req, ctx):
        return get_correlation_id()

    res = interceptor._handle_unary("req", MagicMock(), handler, call_details)
    assert res == "corr-123"


@pytest.mark.anyio
async def test_async_correlation_interceptor_propagates():
    interceptor = AsyncCorrelationServerInterceptor()
    call_details = MagicMock()
    call_details.invocation_metadata = [("x-correlation-id", "corr-async-456")]

    async def async_handler(req, ctx):
        return get_correlation_id()

    res = await interceptor._handle_unary_async(
        "req", AsyncMock(), async_handler, call_details
    )
    assert res == "corr-async-456"
