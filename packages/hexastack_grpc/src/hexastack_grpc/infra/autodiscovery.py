from collections.abc import Sequence
from types import ModuleType
from typing import Any

from hexastack_core.infra.autodiscovery import (
    DiscoveryVisitor,
    scan_modules,
)
from hexastack_grpc.infra.decorators import _GRPC_SERVICE_ATTR
from hexastack_grpc.infra.registries.service import (
    GrpcServiceRegistration,
    GrpcServiceRegistry,
)


def create_grpc_visitor(
    registry: GrpcServiceRegistry,
) -> DiscoveryVisitor:
    """Create a DiscoveryVisitor callback for single-pass gRPC service discovery.

    Notes/Architectural Intent:
        Inspects discovered classes and objects for @grpc_service metadata,
        registering servicers into the supplied service registry during single-pass reflection.

    Args:
        registry: Target GrpcServiceRegistry instance.

    Returns:
        DiscoveryVisitor callable accepting (member, module).
    """

    def visitor(obj: Any, module: ModuleType) -> None:
        meta: GrpcServiceRegistration | None = getattr(obj, _GRPC_SERVICE_ATTR, None)
        if meta is not None:
            registry.register_service(
                servicer=meta.servicer,
                add_to_server_fn=meta.add_to_server_fn,
                service_names=meta.service_names,
            )

    return visitor


def autodiscover_grpc_services(
    packages_to_scan: Sequence[str | ModuleType],
    registry: GrpcServiceRegistry,
) -> GrpcServiceRegistry:
    """Discover decorated gRPC servicers from packages.

    Args:
        packages_to_scan: Sequence of package names or module objects to inspect.
        registry: Target GrpcServiceRegistry instance.

    Returns:
        The populated GrpcServiceRegistry instance.
    """
    visitor = create_grpc_visitor(registry)
    scan_modules(packages_to_scan, [visitor])
    return registry


__all__ = [
    "autodiscover_grpc_services",
    "create_grpc_visitor",
]
