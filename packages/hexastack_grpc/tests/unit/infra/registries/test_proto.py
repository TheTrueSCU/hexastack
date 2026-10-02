"""Unit tests for gRPC proto registries."""

from hexastack_grpc.infra.registries.proto import ProtoRegistry


def test_proto_registry_instantiation() -> None:
    reg = ProtoRegistry()
    assert reg is not None
