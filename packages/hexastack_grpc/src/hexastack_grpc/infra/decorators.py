from collections.abc import Callable, Sequence
from typing import Any

from hexastack_grpc.infra.registries.service import (
    GrpcServiceRegistration,
    GrpcServiceRegistry,
)

_GRPC_SERVICE_ATTR = "__hexastack_grpc_service__"

_default_registry = GrpcServiceRegistry()


__all__ = [
    "get_grpc_registry",
    "grpc_service",
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
