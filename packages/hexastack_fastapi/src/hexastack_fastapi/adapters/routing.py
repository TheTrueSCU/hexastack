import inspect
from collections.abc import Callable
from enum import Enum
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends

from hexastack_core.domain import Command, Query
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_fastapi.adapters.dependencies import get_pipeline
from hexastack_fastapi.adapters.sse import EventSourceResponse


class CqrsRouter(APIRouter):
    """APIRouter providing direct endpoint registration for CQRS Commands and Queries.

    Notes/Architectural Intent:
        Eliminates boilerplate HTTP controller code by binding domain Command and Query
        schemas directly to FastAPI endpoint routes dispatched via ExecutionPipeline.
    """

    def add_command[TCommand: Command](
        self,
        path: str,
        command_cls: type[TCommand],
        *,
        method: str = "POST",
        status_code: int = 200,
        output_format: str | None = None,
        summary: str | None = None,
        tags: list[str | Enum] | None = None,
        feature_flag: str | None = None,
        rate_limit: str | None = None,
    ) -> None:
        """Register an HTTP endpoint for executing a domain Command.

        Args:
            path: URL path for the route.
            command_cls: Pydantic Command model class.
            method: HTTP method (e.g., 'POST', 'PUT', 'DELETE').
            status_code: Success HTTP status code.
            output_format: Optional presenter format (e.g., 'json').
            summary: Optional OpenAPI summary string.
            tags: Optional OpenAPI tags list.
            feature_flag: Optional feature flag key required for endpoint execution.
            rate_limit: Optional rate limit string (e.g. '10/minute').

        Returns:
            None.

        Raises:
            None.
        """
        endpoint = _create_command_endpoint(command_cls, output_format)
        dependencies = []
        if feature_flag:
            from hexastack_fastapi.adapters.dependencies import require_feature

            dependencies.append(Depends(require_feature(feature_flag)))
        if rate_limit:
            from hexastack_fastapi.adapters.dependencies import require_rate_limit

            dependencies.append(Depends(require_rate_limit(rate_limit)))

        self.add_api_route(
            path=path,
            endpoint=endpoint,
            methods=[method.upper()],
            status_code=status_code,
            summary=summary or f"Execute {command_cls.__name__}",
            tags=tags,
            dependencies=dependencies if dependencies else None,
            response_model=None,
        )

    def add_query[TQuery: Query](
        self,
        path: str,
        query_cls: type[TQuery],
        *,
        method: str = "GET",
        status_code: int = 200,
        output_format: str | None = None,
        summary: str | None = None,
        tags: list[str | Enum] | None = None,
        feature_flag: str | None = None,
        rate_limit: str | None = None,
    ) -> None:
        """Register an HTTP endpoint for executing a domain Query.

        Args:
            path: URL path for the route.
            query_cls: Pydantic Query model class.
            method: HTTP method (e.g., 'GET' or 'POST').
            status_code: Success HTTP status code.
            output_format: Optional presenter format (e.g., 'json').
            summary: Optional OpenAPI summary string.
            tags: Optional OpenAPI tags list.
            feature_flag: Optional feature flag key required for endpoint execution.
            rate_limit: Optional rate limit string (e.g. '10/minute').

        Returns:
            None.

        Raises:
            None.
        """
        endpoint = _create_query_endpoint(query_cls, method, output_format)
        dependencies = []
        if feature_flag:
            from hexastack_fastapi.adapters.dependencies import require_feature

            dependencies.append(Depends(require_feature(feature_flag)))
        if rate_limit:
            from hexastack_fastapi.adapters.dependencies import require_rate_limit

            dependencies.append(Depends(require_rate_limit(rate_limit)))

        self.add_api_route(
            path=path,
            endpoint=endpoint,
            methods=[method.upper()],
            status_code=status_code,
            summary=summary or f"Execute {query_cls.__name__}",
            tags=tags,
            dependencies=dependencies if dependencies else None,
            response_model=None,
        )

    def add_streaming_query[TQuery: Query](
        self,
        path: str,
        query_cls: type[TQuery],
        *,
        method: str = "GET",
        summary: str | None = None,
        tags: list[str | Enum] | None = None,
        feature_flag: str | None = None,
        rate_limit: str | None = None,
        ping_interval: float | None = None,
    ) -> None:
        """Register a Server-Sent Events (SSE) streaming endpoint for a Query model.

        Args:
            path: URL path for the route.
            query_cls: Pydantic Query model class.
            method: HTTP method (e.g. 'GET' or 'POST').
            summary: Optional OpenAPI summary string.
            tags: Optional OpenAPI tags list.
            feature_flag: Optional feature flag key required for endpoint execution.
            rate_limit: Optional rate limit string (e.g. '10/minute').
            ping_interval: Optional keep-alive ping interval in seconds.

        Returns:
            None.
        """
        endpoint = _create_streaming_query_endpoint(query_cls, method, ping_interval)
        dependencies = []
        if feature_flag:
            from hexastack_fastapi.adapters.dependencies import require_feature

            dependencies.append(Depends(require_feature(feature_flag)))
        if rate_limit:
            from hexastack_fastapi.adapters.dependencies import require_rate_limit

            dependencies.append(Depends(require_rate_limit(rate_limit)))

        self.add_api_route(
            path=path,
            endpoint=endpoint,
            methods=[method.upper()],
            status_code=200,
            summary=summary or f"Stream {query_cls.__name__}",
            tags=tags,
            dependencies=dependencies if dependencies else None,
            response_class=EventSourceResponse,
        )


__all__ = [
    "CqrsRouter",
]


def _create_command_endpoint(
    command_cls: type[Command], output_format: str | None
) -> Callable[..., Any]:
    """Dynamically construct a typed FastAPI endpoint for a Command model."""

    async def endpoint(
        cmd: Any,
        pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    ) -> Any:
        return pipeline.execute(cmd, output_format=output_format)

    sig = inspect.signature(endpoint)
    params = [
        inspect.Parameter(
            "cmd",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=command_cls,
        ),
        inspect.Parameter(
            "pipeline",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=ExecutionPipeline,
            default=Depends(get_pipeline),
        ),
    ]
    cast("Any", endpoint).__signature__ = sig.replace(parameters=params)
    return endpoint


def _create_query_endpoint(
    query_cls: type[Query], method: str, output_format: str | None
) -> Callable[..., Any]:
    """Dynamically construct a typed FastAPI endpoint for a Query model."""
    if method.upper() == "GET":

        async def get_endpoint(
            qry: Any,
            pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
        ) -> Any:
            return pipeline.execute(qry, output_format=output_format)

        sig = inspect.signature(get_endpoint)
        params = [
            inspect.Parameter(
                "qry",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=query_cls,
                default=Depends(query_cls),
            ),
            inspect.Parameter(
                "pipeline",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=ExecutionPipeline,
                default=Depends(get_pipeline),
            ),
        ]
        cast("Any", get_endpoint).__signature__ = sig.replace(parameters=params)
        return get_endpoint

    async def post_endpoint(
        qry: Any,
        pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    ) -> Any:
        return pipeline.execute(qry, output_format=output_format)

    sig = inspect.signature(post_endpoint)
    params = [
        inspect.Parameter(
            "qry",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=query_cls,
        ),
        inspect.Parameter(
            "pipeline",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=ExecutionPipeline,
            default=Depends(get_pipeline),
        ),
    ]
    cast("Any", post_endpoint).__signature__ = sig.replace(parameters=params)
    return post_endpoint


def _create_streaming_query_endpoint(
    query_cls: type[Query], method: str, ping_interval: float | None
) -> Callable[..., Any]:
    """Dynamically construct an SSE streaming FastAPI endpoint for a Query model."""
    if method.upper() == "GET":

        async def get_stream_endpoint(
            qry: Any,
            pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
        ) -> EventSourceResponse:
            gen = pipeline.execute(qry)
            return EventSourceResponse(gen, ping_interval=ping_interval)

        sig = inspect.signature(get_stream_endpoint)
        params = [
            inspect.Parameter(
                "qry",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=query_cls,
                default=Depends(query_cls),
            ),
            inspect.Parameter(
                "pipeline",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=ExecutionPipeline,
                default=Depends(get_pipeline),
            ),
        ]
        cast("Any", get_stream_endpoint).__signature__ = sig.replace(parameters=params)
        return get_stream_endpoint

    async def post_stream_endpoint(
        qry: Any,
        pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    ) -> EventSourceResponse:
        gen = pipeline.execute(qry)
        return EventSourceResponse(gen, ping_interval=ping_interval)

    sig = inspect.signature(post_stream_endpoint)
    params = [
        inspect.Parameter(
            "qry",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=query_cls,
        ),
        inspect.Parameter(
            "pipeline",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=ExecutionPipeline,
            default=Depends(get_pipeline),
        ),
    ]
    cast("Any", post_stream_endpoint).__signature__ = sig.replace(parameters=params)
    return post_stream_endpoint
