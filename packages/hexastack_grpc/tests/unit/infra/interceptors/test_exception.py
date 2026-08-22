"""Unit tests for gRPC exception interceptors."""

from hexastack_grpc.infra.interceptors.exception import (
    AsyncExceptionServerInterceptor,
    ExceptionServerInterceptor,
)


def test_grpc_exception_interceptors_instantiation() -> None:
    sync_interceptor = ExceptionServerInterceptor()
    async_interceptor = AsyncExceptionServerInterceptor()
    assert sync_interceptor is not None
    assert async_interceptor is not None
