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
