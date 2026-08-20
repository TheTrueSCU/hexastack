from hexastack_fastapi.adapters.app import create_fastapi_app
from hexastack_fastapi.adapters.dependencies import (
    check_openapi_conformance,
    create_test_client,
    get_container,
    get_feature_flags,
    get_pipeline,
    require_feature,
)
from hexastack_fastapi.adapters.docs import (
    DocumentationNotFoundError,
    mount_zensical_docs,
)
from hexastack_fastapi.adapters.health import create_health_router
from hexastack_fastapi.adapters.routing import CqrsRouter
from hexastack_fastapi.adapters.ui import (
    dispatch_command,
    dispatch_query,
    mount_devtools_dashboard,
    mount_ui_app,
    ui_page,
)

__all__ = [
    "check_openapi_conformance",
    "CqrsRouter",
    "create_fastapi_app",
    "create_health_router",
    "create_test_client",
    "dispatch_command",
    "dispatch_query",
    "DocumentationNotFoundError",
    "get_container",
    "get_feature_flags",
    "get_pipeline",
    "mount_devtools_dashboard",
    "mount_ui_app",
    "mount_zensical_docs",
    "require_feature",
    "ui_page",
]
