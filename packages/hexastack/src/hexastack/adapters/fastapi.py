import importlib.util
import sys
from typing import Any

from hexastack.domain.diagnostics import (
    GetSystemInfoQuery,
    InspectRegistryQuery,
    PingDemoCommand,
)
from hexastack_core.infra.bootstrap import bootstrap
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
    import hexastack.application.diagnostics

    current_module = sys.modules[__name__]
    result = bootstrap(
        packages_to_scan=[
            hexastack.application.diagnostics,
            current_module,
        ],
    )
    app = result.get("app")

    # Automatically register demo feature flags for interactive DevTools exploration
    from rodi import InstanceResolver

    from hexastack_core.adapters.feature_flags.in_memory import (
        InMemoryFeatureFlagAdapter,
    )
    from hexastack_core.ports.feature_flags import FeatureFlagPort

    demo_flags = InMemoryFeatureFlagAdapter(
        {
            "features.beta_ui": True,
            "features.dark_mode": True,
            "features.experimental_ai": False,
            "features.rate_limiting": True,
        }
    )
    result.container._map[FeatureFlagPort] = InstanceResolver(demo_flags)

    # Automatically mount NiceGUI DevTools dashboard if hexastack-ui installed
    if app is not None and importlib.util.find_spec("hexastack_ui") is not None:
        try:
            from hexastack_ui.adapters.nicegui import mount_devtools_dashboard

            mount_devtools_dashboard(
                app,
                container=result.container,
                pipeline=result.properties.get("pipeline"),
                path="/_devtools",
            )
        except Exception:
            # DevTools mounting is optional and non-critical; pass silently on failure
            pass

    return app
