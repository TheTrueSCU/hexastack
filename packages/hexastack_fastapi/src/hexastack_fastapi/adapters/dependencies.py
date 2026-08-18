from fastapi import Request
from rodi import Container

from hexastack_core.domain.exceptions import DependencyResolutionError
from hexastack_cqrs.infra.pipeline import ExecutionPipeline

__all__ = [
    "get_container",
    "get_pipeline",
]


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
