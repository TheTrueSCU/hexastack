import contextlib
import sys
from typing import Any

import hexastack.application.diagnostics
from hexastack.domain.diagnostics import (
    GetSystemInfoQuery,
    InspectRegistryQuery,
    PingDemoCommand,
)
from hexastack_core.adapters.feature_flags.in_memory import (
    InMemoryFeatureFlagAdapter,
)
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.infra.container import create_container
from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_core.utils.imports import optional_dependency
from hexastack_fastapi.infra.decorators import (
    api_command,
    api_query,
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


__all__ = [
    "create_demo_app",
]


def create_demo_app() -> Any:
    """Instantiate a fully configured FastAPI application with Hexastack diagnostics.

    Returns:
        FastAPI application instance.

    Raises:
        None.
    """
    demo_flags = InMemoryFeatureFlagAdapter(
        {
            "features.beta_ui": True,
            "features.dark_mode": True,
            "features.experimental_ai": False,
            "features.rate_limiting": True,
        }
    )
    container = create_container()
    container.add_instance(demo_flags, declared_class=FeatureFlagPort)

    current_module = sys.modules[__name__]
    result = bootstrap(
        container=container,
        packages_to_scan=[
            hexastack.application.diagnostics,
            current_module,
        ],
    )
    app = result.get("app")

    # Automatically mount NiceGUI DevTools dashboard if hexastack-ui installed
    ui_module = optional_dependency("hexastack_ui.adapters.nicegui")
    if (
        app is not None
        and ui_module is not None
        and hasattr(ui_module, "mount_devtools_dashboard")
    ):
        with contextlib.suppress(Exception):
            ui_module.mount_devtools_dashboard(
                app,
                container=result.container,
                pipeline=result.properties.get("pipeline"),
                path="/_devtools",
            )

    return app
