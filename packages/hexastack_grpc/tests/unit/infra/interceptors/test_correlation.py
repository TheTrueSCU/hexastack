"""Unit tests for gRPC correlation interceptors."""

from hexastack_grpc.infra.interceptors.correlation import (
    AsyncCorrelationServerInterceptor,
    CorrelationServerInterceptor,
)


def test_grpc_correlation_interceptors_instantiation() -> None:
    sync_interceptor = CorrelationServerInterceptor()
    async_interceptor = AsyncCorrelationServerInterceptor()
    assert sync_interceptor is not None
    assert async_interceptor is not None
