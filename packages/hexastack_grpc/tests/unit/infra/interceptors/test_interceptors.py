from typing import Any
from unittest.mock import MagicMock

import grpc
from hexastack_core.domain.exceptions import NotFoundError, ValidationError
from hexastack_core.utils.context import get_correlation_id
from hexastack_grpc.infra.interceptors.correlation import (
    CorrelationServerInterceptor,
)
from hexastack_grpc.infra.interceptors.exception import (
    ExceptionServerInterceptor,
)
from hexastack_grpc.infra.interceptors.logging import (
    LoggingServerInterceptor,
    TimingServerInterceptor,
)


def test_correlation_interceptor_propagates_metadata():
    interceptor = CorrelationServerInterceptor()

    def dummy_handler(request: Any, context: Any) -> str:
        return get_correlation_id()

    rpc_handler = grpc.unary_unary_rpc_method_handler(dummy_handler)
    continuation = MagicMock(return_value=rpc_handler)

    call_details = MagicMock()
    call_details.invocation_metadata = [("x-correlation-id", "grpc-trace-12345")]

    intercepted: Any = interceptor.intercept_service(continuation, call_details)
    assert intercepted is not None
    assert getattr(intercepted, "unary_unary", None) is not None

    mock_context = MagicMock()
    result_cid = intercepted.unary_unary("req", mock_context)
    assert result_cid == "grpc-trace-12345"


def test_exception_interceptor_maps_status_codes():
    interceptor = ExceptionServerInterceptor()

    # 1. NotFoundError mapping
    def not_found_handler(request: Any, context: Any) -> Any:
        raise NotFoundError("Resource item-42 not found")

    rpc_handler = grpc.unary_unary_rpc_method_handler(not_found_handler)
    continuation = MagicMock(return_value=rpc_handler)

    call_details = MagicMock()
    call_details.method = "/test.Service/GetItem"

    intercepted: Any = interceptor.intercept_service(continuation, call_details)
    mock_context = MagicMock()

    intercepted.unary_unary("req", mock_context)
    mock_context.abort.assert_called_once_with(
        grpc.StatusCode.NOT_FOUND,
        "Resource item-42 not found",
    )

    # 2. ValidationError mapping
    def validation_handler(request: Any, context: Any) -> Any:
        raise ValidationError("Invalid argument: price negative")

    rpc_handler2 = grpc.unary_unary_rpc_method_handler(validation_handler)
    continuation2 = MagicMock(return_value=rpc_handler2)

    intercepted2: Any = interceptor.intercept_service(continuation2, call_details)
    mock_context2 = MagicMock()

    intercepted2.unary_unary("req", mock_context2)
    mock_context2.abort.assert_called_once_with(
        grpc.StatusCode.INVALID_ARGUMENT,
        "Invalid argument: price negative",
    )


def test_logging_and_timing_interceptors():
    log_interceptor = LoggingServerInterceptor()
    time_interceptor = TimingServerInterceptor()

    def dummy_handler(request: Any, context: Any) -> str:
        return "response"

    rpc_handler = grpc.unary_unary_rpc_method_handler(dummy_handler)
    continuation = MagicMock(return_value=rpc_handler)

    call_details = MagicMock()
    call_details.method = "/test.Service/SayHello"

    h1: Any = log_interceptor.intercept_service(continuation, call_details)
    assert h1 is not None and getattr(h1, "unary_unary", None) is not None
    assert h1.unary_unary("req", MagicMock()) == "response"

    h2: Any = time_interceptor.intercept_service(continuation, call_details)
    assert h2 is not None and getattr(h2, "unary_unary", None) is not None
    assert h2.unary_unary("req", MagicMock()) == "response"
