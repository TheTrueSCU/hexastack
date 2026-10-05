"""Unit tests for gRPC domain models."""

from hexastack_grpc.domain.models import ProtoSchemaMetadata


def test_proto_schema_metadata_model() -> None:
    meta = ProtoSchemaMetadata(target="order_service", message_name="CreateOrder")
    assert meta.target == "order_service"
    assert meta.message_name == "CreateOrder"
