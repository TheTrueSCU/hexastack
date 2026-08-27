"""Unit tests for gRPC logging interceptors."""

from hexastack_grpc.infra.interceptors.logging import (
    LoggingServerInterceptor,
    TimingServerInterceptor,
)


def test_grpc_logging_interceptors_instantiation() -> None:
    log_interceptor = LoggingServerInterceptor()
    time_interceptor = TimingServerInterceptor()
    assert log_interceptor is not None
    assert time_interceptor is not None


def test_logging_server_interceptor_execution_and_error():
    """Verify LoggingServerInterceptor handles successful execution and exceptions."""
    from unittest.mock import MagicMock

    import pytest

    interceptor = LoggingServerInterceptor()
    mock_details = MagicMock()
    mock_details.method = "/demo.Service/SayHello"

    # 1. Success path
    res = interceptor._handle_unary(
        request="req",
        context=MagicMock(),
        unary_fn=lambda r, c: f"hello {r}",
        handler_call_details=mock_details,
    )
    assert res == "hello req"

    # 2. Exception path
    def failing_unary(r, c):
        raise ValueError("simulated rpc error")

    with pytest.raises(ValueError, match="simulated rpc error"):
        interceptor._handle_unary(
            request="req",
            context=MagicMock(),
            unary_fn=failing_unary,
            handler_call_details=mock_details,
        )


def test_timing_server_interceptor_execution():
    """Verify TimingServerInterceptor handles unary call execution and latency tracking."""
    from unittest.mock import MagicMock

    interceptor = TimingServerInterceptor()
    mock_details = MagicMock()
    mock_details.method = "/demo.Service/Ping"

    res = interceptor._handle_unary(
        request="ping",
        context=MagicMock(),
        unary_fn=lambda r, c: "pong",
        handler_call_details=mock_details,
    )
    assert res == "pong"
