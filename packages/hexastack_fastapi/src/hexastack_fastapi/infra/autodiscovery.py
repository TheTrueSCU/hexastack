import inspect
from collections.abc import Sequence
from types import ModuleType
from typing import Any

from fastapi import FastAPI

from hexastack_core.domain import Command, Query
from hexastack_core.infra.autodiscovery import (
    DiscoveryVisitor,
    scan_modules,
)
from hexastack_fastapi.adapters.routing import CqrsRouter
from hexastack_fastapi.infra.decorators import (
    _ROUTE_METADATA_ATTR,
    RouteMetadata,
)


def create_route_visitor(router: CqrsRouter) -> DiscoveryVisitor:
    """Create a DiscoveryVisitor callback for single-pass HTTP route registration.

    Notes/Architectural Intent:
        Inspects discovered classes for @api_command and @api_query metadata,
        mounting them onto the supplied CqrsRouter without duplicate reflection loops.

    Args:
        router: Target CqrsRouter instance.

    Returns:
        DiscoveryVisitor callable accepting (member, module).

    Raises:
        None.
    """

    def visitor(obj: Any, module: ModuleType) -> None:
        if not inspect.isclass(obj):
            return

        meta: RouteMetadata | None = getattr(obj, _ROUTE_METADATA_ATTR, None)
        if meta is None:
            return

        tags = list(meta.tags) if meta.tags else None
        if (
            meta.kind == "command"
            and isinstance(obj, type)
            and issubclass(obj, Command)
        ):
            router.add_command(
                path=meta.path,
                command_cls=obj,
                method=meta.method,
                status_code=meta.status_code,
                output_format=meta.output_format,
                summary=meta.summary,
                tags=tags,
            )
        elif meta.kind == "query" and isinstance(obj, type) and issubclass(obj, Query):
            router.add_query(
                path=meta.path,
                query_cls=obj,
                method=meta.method,
                status_code=meta.status_code,
                output_format=meta.output_format,
                summary=meta.summary,
                tags=tags,
            )

    return visitor


def autodiscover_routes(
    app: FastAPI,
    packages_to_scan: Sequence[str | ModuleType],
    router: CqrsRouter | None = None,
) -> CqrsRouter:
    """Automatically discover decorated routes from packages and attach them to a FastAPI application.

    Args:
        app: Target FastAPI application instance.
        packages_to_scan: Sequence of package names or module objects to inspect.
        router: Optional CqrsRouter instance to populate and mount.

    Returns:
        The mounted CqrsRouter instance.

    Raises:
        None.
    """
    target_router = router or CqrsRouter()
    visitor = create_route_visitor(target_router)
    scan_modules(packages_to_scan, [visitor])
    app.include_router(target_router)
    return target_router


__all__ = [
    "autodiscover_routes",
    "create_route_visitor",
]
