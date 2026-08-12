import inspect
from collections.abc import Callable
from enum import Enum
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends
from hexastack_core.domain import Command, Query
from hexastack_cqrs.infra.pipeline import ExecutionPipeline

from hexastack_fastapi.adapters.dependencies import get_pipeline


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
    cast(Any, endpoint).__signature__ = sig.replace(parameters=params)
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
        cast(Any, get_endpoint).__signature__ = sig.replace(parameters=params)
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
    cast(Any, post_endpoint).__signature__ = sig.replace(parameters=params)
    return post_endpoint


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

        Returns:
            None.

        Raises:
            None.
        """
        endpoint = _create_command_endpoint(command_cls, output_format)
        self.add_api_route(
            path=path,
            endpoint=endpoint,
            methods=[method.upper()],
            status_code=status_code,
            summary=summary or f"Execute {command_cls.__name__}",
            tags=tags,
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
    ) -> None:
        """Register an HTTP endpoint for executing a domain Query.

        Args:
            path: URL path for the route.
            query_cls: Pydantic Query model class.
            method: HTTP method ('GET' or 'POST').
            status_code: Success HTTP status code.
            output_format: Optional presenter format (e.g., 'json').
            summary: Optional OpenAPI summary string.
            tags: Optional OpenAPI tags list.

        Returns:
            None.

        Raises:
            None.
        """
        endpoint = _create_query_endpoint(query_cls, method, output_format)
        self.add_api_route(
            path=path,
            endpoint=endpoint,
            methods=[method.upper()],
            status_code=status_code,
            summary=summary or f"Execute {query_cls.__name__}",
            tags=tags,
            response_model=None,
        )


__all__ = [
    "CqrsRouter",
]
