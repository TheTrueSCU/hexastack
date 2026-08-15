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


def test_exception_interceptor_passes_through_none_handler():
    """GenericServerInterceptor guard: None handler is returned as-is."""
    interceptor = ExceptionServerInterceptor()
    continuation = MagicMock(return_value=None)
    call_details = MagicMock()
    call_details.invocation_metadata = []
    result = interceptor.intercept_service(continuation, call_details)
    assert result is None


def test_exception_interceptor_passes_through_non_unary_handler():
    """GenericServerInterceptor guard: handler without unary_unary is passed through."""
    interceptor = ExceptionServerInterceptor()
    handler = MagicMock(spec=[])  # no unary_unary attribute
    continuation = MagicMock(return_value=handler)
    call_details = MagicMock()
    call_details.invocation_metadata = []
    result = interceptor.intercept_service(continuation, call_details)
    assert result is handler


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
