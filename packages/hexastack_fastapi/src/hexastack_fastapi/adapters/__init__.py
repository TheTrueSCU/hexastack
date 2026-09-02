from hexastack_fastapi.adapters.dependencies import (
    check_openapi_conformance,
    create_test_client,
    get_container,
    get_feature_flags,
    get_pipeline,
    get_rate_limiter,
    require_feature,
    require_rate_limit,
)
from hexastack_fastapi.adapters.docs import (
    DocumentationNotFoundError,
    mount_zensical_docs,
)
from hexastack_fastapi.adapters.health import create_health_router
from hexastack_fastapi.adapters.ratelimit import (
    SlowapiRateLimiterAdapter,
    get_remote_address,
    get_user_or_ip_key,
    rate_limit,
)
from hexastack_fastapi.adapters.routing import CqrsRouter
from hexastack_fastapi.adapters.ui import (
    dispatch_command,
    dispatch_query,
    mount_devtools_dashboard,
    mount_ui_app,
    ui_page,
)

__all__ = [
    "CqrsRouter",
    "DocumentationNotFoundError",
    "SlowapiRateLimiterAdapter",
    "check_openapi_conformance",
    "create_fastapi_app",
    "create_health_router",
    "create_test_client",
    "dispatch_command",
    "dispatch_query",
    "get_container",
    "get_feature_flags",
    "get_pipeline",
    "get_rate_limiter",
    "get_remote_address",
    "get_user_or_ip_key",
    "mount_devtools_dashboard",
    "mount_ui_app",
    "mount_zensical_docs",
    "rate_limit",
    "require_feature",
    "require_rate_limit",
    "ui_page",
]
