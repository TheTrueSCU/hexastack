"""Unit tests for GrpcHealthServicer adapter."""

from __future__ import annotations

from grpc_health.v1 import health_pb2

from hexastack_grpc.adapters.health import GrpcHealthServicer


def test_grpc_health_servicer_lifecycle() -> None:
    """Verify GrpcHealthServicer sets and checks serving status."""
    servicer = GrpcHealthServicer()

    # Initial overall status defaults to SERVING
    req_overall = health_pb2.HealthCheckRequest(service="")
    res_overall = servicer.Check(req_overall, context=None)
    assert res_overall.status == health_pb2.HealthCheckResponse.ServingStatus.SERVING

    # Set specific service to NOT_SERVING
    servicer.set_not_serving("UserService")
    req_user = health_pb2.HealthCheckRequest(service="UserService")
    res_user = servicer.Check(req_user, context=None)
    assert res_user.status == health_pb2.HealthCheckResponse.ServingStatus.NOT_SERVING

    # Set back to SERVING
    servicer.set_serving("UserService")
    res_user2 = servicer.Check(req_user, context=None)
    assert res_user2.status == health_pb2.HealthCheckResponse.ServingStatus.SERVING
