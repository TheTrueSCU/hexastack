from typing import Any

from fastapi import HTTPException, Request, status
from rodi import Container

from hexastack_core.adapters.feature_flags.config import ConfigFeatureFlagAdapter
from hexastack_core.adapters.feature_flags.in_memory import InMemoryFeatureFlagAdapter
from hexastack_core.domain.exceptions import (
    DependencyResolutionError,
    MissingDependencyError,
)
from hexastack_core.domain.feature_flags import EvaluationContext
from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_cqrs.infra.pipeline import ExecutionPipeline

__all__ = [
    "check_openapi_conformance",
    "create_test_client",
    "get_container",
    "get_feature_flags",
    "get_pipeline",
    "require_feature",
]


def check_openapi_conformance(
    app: Any,
    *,
    schema_url: str = "/openapi.json",
    validate_schema: bool = True,
) -> None:
    """Run Schemathesis contract conformance and schema validation checks against a FastAPI app.

    Notes/Architectural Intent:
        Automatically tests that all exposed FastAPI endpoints conform to the
        derived OpenAPI schema, validate properly, and have complete route definitions.

    Args:
        app: The FastAPI application instance.
        schema_url: URL path where the OpenAPI JSON is served (defaults to '/openapi.json').
        validate_schema: Whether to validate the OpenAPI specification structure itself.

    Raises:
        MissingDependencyError: If `schemathesis` is not installed.
        AssertionError: If any API contract violation or unhandled error is detected.
    """
    try:
        import schemathesis
    except ImportError as e:
        raise MissingDependencyError(
            "schemathesis is required for check_openapi_conformance. "
            "Install with 'pip install schemathesis' or 'pip install hexastack[testing]'."
        ) from e

    schema = schemathesis.openapi.from_asgi(schema_url, app)

    if validate_schema:
        schema.validate()


def create_test_client(
    app: Any,
    *,
    flags: dict[str, Any] | None = None,
    **test_client_kwargs: Any,
) -> Any:
    """Create a FastAPI TestClient configured with an in-memory feature flag adapter.

    Args:
        app: The FastAPI application instance.
        flags: Optional initial flag states.
        **test_client_kwargs: Extra keyword arguments forwarded to TestClient.

    Returns:
        Configured starlette / fastapi TestClient.
    """
    from fastapi.testclient import TestClient

    if flags is not None:
        container = getattr(app.state, "container", None)
        flags_adapter = InMemoryFeatureFlagAdapter(flags=flags)
        if container is not None:
            container.add_instance(flags_adapter, declared_class=FeatureFlagPort)

    return TestClient(app, **test_client_kwargs)


def get_container(request: Request) -> Container:
    """FastAPI dependency provider resolving the active rodi Container instance.

    Notes/Architectural Intent:
        Enables endpoint routes to inject and resolve registered domain ports and services.

    Args:
        request: Incoming FastAPI Request object.

    Returns:
        The rodi Container attached to the application state.

    Raises:
        DependencyResolutionError: If Container has not been attached to app.state.
    """
    container = getattr(request.app.state, "container", None)
    if container is None or not isinstance(container, Container):
        raise DependencyResolutionError(
            "rodi.Container is not configured on request.app.state.container."
        )
    return container


def get_feature_flags(request: Request) -> FeatureFlagPort:
    """FastAPI dependency provider resolving the active FeatureFlagPort instance.

    Notes/Architectural Intent:
        Retrieves the registered FeatureFlagPort from the application container or
        falls back to ConfigFeatureFlagAdapter.

    Args:
        request: Incoming FastAPI Request object.

    Returns:
        The FeatureFlagPort instance.
    """
    container = getattr(request.app.state, "container", None)
    if isinstance(container, Container) and FeatureFlagPort in container:
        return container.resolve(FeatureFlagPort)
    return ConfigFeatureFlagAdapter()


def get_pipeline(request: Request) -> ExecutionPipeline:
    """FastAPI dependency provider resolving the active ExecutionPipeline instance.

    Notes/Architectural Intent:
        Enables route handlers to execute CQRS commands and queries through the unified pipeline.

    Args:
        request: Incoming FastAPI Request object.

    Returns:
        The ExecutionPipeline instance attached to application state or resolved from DI.

    Raises:
        DependencyResolutionError: If ExecutionPipeline cannot be resolved from application state or container.
    """
    pipeline = getattr(request.app.state, "pipeline", None)
    if isinstance(pipeline, ExecutionPipeline):
        return pipeline

    container = getattr(request.app.state, "container", None)
    if isinstance(container, Container) and ExecutionPipeline in container:
        return container.resolve(ExecutionPipeline)

    raise DependencyResolutionError(
        "ExecutionPipeline is not available on request.app.state.pipeline or container."
    )


def require_feature(
    flag_key: str,
    *,
    default: bool = False,
    status_code: int = status.HTTP_404_NOT_FOUND,
    detail: str | None = None,
) -> Any:
    """Create a FastAPI dependency that enforces a feature flag is enabled.

    Notes/Architectural Intent:
        Evaluates the feature flag dynamically against ambient UserContext / request state.
        If disabled, raises an HTTPException (default 404 Not Found) to cleanly hide or gate routes.

    Args:
        flag_key: Unique identifier of the feature flag to check.
        default: Fallback boolean value if flag is not explicitly configured.
        status_code: HTTP status code to return when disabled (defaults to 404).
        detail: Optional error detail message.

    Returns:
        A FastAPI dependency callable.
    """

    async def _dependency(request: Request) -> None:
        flags = get_feature_flags(request)
        eval_ctx = EvaluationContext.from_current_context()
        if not flags.is_enabled(flag_key, default=default, context=eval_ctx):
            raise HTTPException(
                status_code=status_code,
                detail=detail or f"Feature '{flag_key}' is disabled.",
            )

    return _dependency
