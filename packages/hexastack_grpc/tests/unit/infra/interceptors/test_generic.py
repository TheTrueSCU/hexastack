from typing import Any
from unittest.mock import MagicMock

import grpc
import pytest

from hexastack_core.domain.exceptions import (
    HexastackError,
    NotFoundError,
    ValidationError,
)
from hexastack_core.utils.context import get_correlation_id
from hexastack_grpc.infra.interceptors.correlation import (
    CorrelationServerInterceptor,
)
from hexastack_grpc.infra.interceptors.exception import (
    ExceptionServerInterceptor,
    _map_exception_to_status_code,
)
from hexastack_grpc.infra.interceptors.logging import (
    LoggingServerInterceptor,
    TimingServerInterceptor,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_intercepted(
    interceptor: grpc.ServerInterceptor,
    handler_fn: Any,
    method: str = "/test.Service/Method",
    metadata: list | None = None,
) -> Any:
    """Wire handler through interceptor and return the wrapped handler."""
    rpc_handler = grpc.unary_unary_rpc_method_handler(handler_fn)
    continuation = MagicMock(return_value=rpc_handler)
    call_details = MagicMock()
    call_details.method = method
    call_details.invocation_metadata = metadata or []
    return interceptor.intercept_service(continuation, call_details)


def test_correlation_interceptor_bytes_metadata():
    """Kills mutant 1367: bytes decode branch in _extract_cid."""
    interceptor = CorrelationServerInterceptor()

    def cid_handler(request: Any, context: Any) -> str:
        return get_correlation_id()

    # Metadata value as bytes (gRPC on-wire encoding)
    intercepted: Any = _make_intercepted(
        interceptor,
        cid_handler,
        metadata=[("x-correlation-id", b"bytes-cid-abc")],
    )
    assert intercepted.unary_unary("req", MagicMock()) == "bytes-cid-abc"


def test_correlation_interceptor_generates_id_when_no_metadata():
    """Kills mutant 1369: ensures cid is extracted from metadata, not skipped."""
    interceptor = CorrelationServerInterceptor()

    def cid_handler(request: Any, context: Any) -> str:
        return get_correlation_id()

    intercepted: Any = _make_intercepted(interceptor, cid_handler, metadata=[])
    cid = intercepted.unary_unary("req", MagicMock())
    assert cid  # auto-generated UUID — truthy
    assert len(cid) == 36  # UUID4 format


# ---------------------------------------------------------------------------
# Correlation interceptor
# ---------------------------------------------------------------------------


def test_correlation_interceptor_propagates_metadata():
    interceptor = CorrelationServerInterceptor()

    def dummy_handler(request: Any, context: Any) -> str:
        return get_correlation_id()

    intercepted: Any = _make_intercepted(
        interceptor,
        dummy_handler,
        metadata=[("x-correlation-id", "grpc-trace-12345")],
    )
    assert intercepted is not None
    assert getattr(intercepted, "unary_unary", None) is not None
    assert intercepted.unary_unary("req", MagicMock()) == "grpc-trace-12345"


def test_exception_interceptor_aborts_with_correct_code():
    """Integration: ExceptionServerInterceptor calls context.abort with mapped code."""
    interceptor = ExceptionServerInterceptor()

    def not_found_handler(request: Any, context: Any) -> Any:
        raise NotFoundError("Resource item-42 not found")

    intercepted: Any = _make_intercepted(interceptor, not_found_handler)
    mock_context = MagicMock()
    intercepted.unary_unary("req", mock_context)
    mock_context.abort.assert_called_once_with(
        grpc.StatusCode.NOT_FOUND,
        "Resource item-42 not found",
    )


def test_exception_interceptor_invalid_argument():
    interceptor = ExceptionServerInterceptor()

    def validation_handler(request: Any, context: Any) -> Any:
        raise ValidationError("Invalid argument: price negative")

    intercepted: Any = _make_intercepted(interceptor, validation_handler)
    mock_context = MagicMock()
    intercepted.unary_unary("req", mock_context)
    mock_context.abort.assert_called_once_with(
        grpc.StatusCode.INVALID_ARGUMENT,
        "Invalid argument: price negative",
    )


def test_exception_interceptor_passes_through_non_unary_handler():
    """GenericServerInterceptor guard: handler without unary_unary is passed through."""
    interceptor = ExceptionServerInterceptor()
    handler = MagicMock(spec=[])  # no unary_unary attribute
    continuation = MagicMock(return_value=handler)
    call_details = MagicMock()
    call_details.invocation_metadata = []
    result = interceptor.intercept_service(continuation, call_details)
    assert result is handler


def test_exception_interceptor_passes_through_none_handler():
    """GenericServerInterceptor guard: None handler is returned as-is."""
    interceptor = ExceptionServerInterceptor()
    continuation = MagicMock(return_value=None)
    call_details = MagicMock()
    call_details.invocation_metadata = []
    result = interceptor.intercept_service(continuation, call_details)
    assert result is None


# ---------------------------------------------------------------------------
# Logging / Timing interceptors
# ---------------------------------------------------------------------------


def test_logging_and_timing_interceptors():
    log_interceptor = LoggingServerInterceptor()
    time_interceptor = TimingServerInterceptor()

    def dummy_handler(request: Any, context: Any) -> str:
        return "response"

    h1: Any = _make_intercepted(
        log_interceptor, dummy_handler, "/test.Service/SayHello"
    )
    assert h1 is not None and getattr(h1, "unary_unary", None) is not None
    assert h1.unary_unary("req", MagicMock()) == "response"

    h2: Any = _make_intercepted(
        time_interceptor, dummy_handler, "/test.Service/SayHello"
    )
    assert h2 is not None and getattr(h2, "unary_unary", None) is not None
    assert h2.unary_unary("req", MagicMock()) == "response"


# ---------------------------------------------------------------------------
# Exception interceptor — one test per status code branch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("exc", "expected_code"),
    [
        (NotFoundError("item-42 not found"), grpc.StatusCode.NOT_FOUND),
        (ValidationError("price is negative"), grpc.StatusCode.INVALID_ARGUMENT),
        (
            type("AuthenticationError", (HexastackError,), {})("bad token"),
            grpc.StatusCode.UNAUTHENTICATED,
        ),
        (
            type("ForbiddenError", (HexastackError,), {})("no access"),
            grpc.StatusCode.PERMISSION_DENIED,
        ),
        (
            type("AlreadyExistsError", (HexastackError,), {})("dup"),
            grpc.StatusCode.ALREADY_EXISTS,
        ),
        (HexastackError("internal failure"), grpc.StatusCode.INTERNAL),
        (RuntimeError("unknown boom"), grpc.StatusCode.UNKNOWN),
    ],
    ids=[
        "not_found",
        "invalid_argument",
        "unauthenticated",
        "permission_denied",
        "already_exists",
        "internal",
        "unknown",
    ],
)
def test_map_exception_to_status_code(
    exc: Exception, expected_code: grpc.StatusCode
) -> None:
    """Kills all 18 mutants in exception.py by exercising every branch of
    _map_exception_to_status_code directly."""
    code, msg = _map_exception_to_status_code(exc)
    assert code == expected_code
    assert msg == str(exc)


@pytest.mark.anyio
async def test_async_interceptor_intercept_service_pipeline():
    """Verify AsyncGenericServerInterceptor.intercept_service wrapping unary calls."""
    from unittest.mock import AsyncMock, MagicMock

    from hexastack_grpc.infra.interceptors.generic import AsyncGenericServerInterceptor

    class DummyAsyncInterceptor(AsyncGenericServerInterceptor):
        async def _handle_unary_async(
            self,
            request: Any,
            context: Any,
            unary_fn: Any,
            handler_call_details: Any,
        ) -> Any:
            res = await unary_fn(request, context)
            return f"{res}-intercepted"

    interceptor = DummyAsyncInterceptor()

    # 1. Non-existent handler continuation returns None
    res_none = await interceptor.intercept_service(
        AsyncMock(return_value=None), MagicMock()
    )
    assert res_none is None

    # 2. Handler without unary_unary
    handler_without_unary = MagicMock(spec=[])
    res_raw = await interceptor.intercept_service(
        AsyncMock(return_value=handler_without_unary), MagicMock()
    )
    assert res_raw is handler_without_unary

    # 3. Handler with unary_unary method
    async def _dummy_rpc(req, ctx):
        return f"hello {req}"

    handler_mock = MagicMock()
    handler_mock.unary_unary = _dummy_rpc
    handler_mock.request_streaming = False
    handler_mock.response_streaming = False
    handler_mock.request_deserializer = None
    handler_mock.response_serializer = None

    wrapped_handler = await interceptor.intercept_service(
        AsyncMock(return_value=handler_mock), MagicMock()
    )
    assert wrapped_handler is not None
    res_val = await wrapped_handler.unary_unary("world", MagicMock())
    assert res_val == "hello world-intercepted"
