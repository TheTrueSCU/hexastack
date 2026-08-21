from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from hexastack_grpc.domain.models import ProtoSchemaMetadata
from hexastack_grpc.infra.registries.proto import get_proto_registry
from hexastack_grpc.infra.registries.service import (
    GrpcServiceRegistration,
    GrpcServiceRegistry,
)

_GRPC_SERVICE_ATTR = "__hexastack_grpc_service__"
_PROTO_SCHEMA_ATTR = "__hexastack_proto_schema__"

_default_registry = GrpcServiceRegistry()


__all__ = [
    "get_grpc_registry",
    "get_proto_registry",
    "grpc_service",
    "proto_file",
    "proto_schema",
]


def get_grpc_registry() -> GrpcServiceRegistry:
    """Return the global default GrpcServiceRegistry instance.

    Returns:
        GrpcServiceRegistry instance.
    """
    return _default_registry


def grpc_service(
    add_to_server_fn: Callable[[Any, Any], None],
    *,
    service_names: Sequence[str] = (),
) -> Callable[[Any], Any]:
    """Decorator registering a gRPC servicer class or instance with its protobuf hook.

    Notes/Architectural Intent:
        Attaches metadata for single-pass module scanning and registers the servicer
        in the default GrpcServiceRegistry.

    Args:
        add_to_server_fn: Generated protobuf hook (e.g. add_UserServiceServicer_to_server).
        service_names: Optional sequence of full service names for reflection.

    Returns:
        Decorator function.
    """

    def decorator(target: Any) -> Any:
        meta = GrpcServiceRegistration(
            servicer=target,
            add_to_server_fn=add_to_server_fn,
            service_names=service_names,
        )
        setattr(target, _GRPC_SERVICE_ATTR, meta)
        _default_registry.register_service(
            servicer=target,
            add_to_server_fn=add_to_server_fn,
            service_names=service_names,
        )
        return target

    return decorator


def proto_schema(
    schema: str,
    message_name: str,
    *,
    service_name: str | None = None,
    rpc_name: str | None = None,
) -> Callable[[Any], Any]:
    """Decorator associating an inline protobuf schema string with a command, query, or servicer.

    Args:
        schema: Protobuf schema definition string (proto3).
        message_name: Target Protobuf message identifier within the schema.
        service_name: Optional associated gRPC service name.
        rpc_name: Optional associated RPC method name.

    Returns:
        Decorator function.
    """

    def decorator(target: Any) -> Any:
        meta: ProtoSchemaMetadata = get_proto_registry().register_schema(
            target=target,
            message_name=message_name,
            schema=schema,
            service_name=service_name,
            rpc_name=rpc_name,
        )
        setattr(target, _PROTO_SCHEMA_ATTR, meta)
        return target

    return decorator


def proto_file(
    file_path: str | Path,
    message_name: str,
    *,
    service_name: str | None = None,
    rpc_name: str | None = None,
) -> Callable[[Any], Any]:
    """Decorator associating an external .proto file path with a command, query, or servicer.

    Args:
        file_path: Path to the source .proto definition file.
        message_name: Target Protobuf message identifier within the file.
        service_name: Optional associated gRPC service name.
        rpc_name: Optional associated RPC method name.

    Returns:
        Decorator function.
    """

    def decorator(target: Any) -> Any:
        meta: ProtoSchemaMetadata = get_proto_registry().register_file(
            target=target,
            message_name=message_name,
            file_path=file_path,
            service_name=service_name,
            rpc_name=rpc_name,
        )
        setattr(target, _PROTO_SCHEMA_ATTR, meta)
        return target

    return decorator
