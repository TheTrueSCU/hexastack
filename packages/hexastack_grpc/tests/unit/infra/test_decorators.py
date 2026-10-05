"""Unit tests for gRPC decorators."""

from hexastack_grpc.infra.decorators import grpc_service


def test_grpc_service_decorator_callable() -> None:
    assert callable(grpc_service)
