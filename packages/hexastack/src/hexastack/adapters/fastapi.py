import sys
from typing import Any

from hexastack_core.infra.bootstrap import bootstrap
from hexastack_fastapi.infra.decorators import (
    api_command,
    api_query,
)

from hexastack.domain.diagnostics import (
    GetSystemInfoQuery,
    InspectRegistryQuery,
    PingDemoCommand,
)

# Decorate domain models with REST endpoints
api_query("/_hexastack/info", summary="Hexastack System Diagnostics")(
    GetSystemInfoQuery
)
api_query("/_hexastack/registry", summary="Hexastack Registry Introspection")(
    InspectRegistryQuery
)
api_command(
    "/_hexastack/ping",
    method="POST",
    summary="Hexastack CQRS Ping Demo",
)(PingDemoCommand)


def create_demo_app() -> Any:
    """Instantiate a fully configured FastAPI application with Hexastack diagnostics.

    Returns:
        FastAPI application instance.

    Raises:
        None.
    """
    import hexastack.application.diagnostics

    current_module = sys.modules[__name__]
    result = bootstrap(
        packages_to_scan=[
            hexastack.application.diagnostics,
            current_module,
        ],
    )
    return result.get("app")


__all__ = [
    "create_demo_app",
]
