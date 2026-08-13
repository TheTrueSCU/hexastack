import importlib.util
from typing import Any

import strawberry
from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_cqrs.ports.buses import CommandBusPort, QueryBusPort
from rodi import Container

from hexastack_graphql.domain.context import GraphQLContext


def _require_fastapi() -> None:
    """Guard against missing FastAPI installation.

    Raises:
        MissingDependencyError: If fastapi is not installed.
    """
    if importlib.util.find_spec("fastapi") is None:
        raise MissingDependencyError(
            "fastapi is required for FastAPI GraphQL integration. "
            "Install via 'pip install hexastack-graphql[fastapi]'."
        )


def create_graphql_router(
    schema: strawberry.Schema,
    container: Container,
    *,
    command_bus: CommandBusPort | None = None,
    query_bus: QueryBusPort | None = None,
    graphiql: bool = True,
) -> Any:
    """Construct a Strawberry GraphQLRouter for FastAPI.

    Notes/Architectural Intent:
        Creates a FastAPI APIRouter subclass (GraphQLRouter) that dynamically
        injects the rodi Container and CQRS message buses into Info.context for
        every HTTP execution.

    Args:
        schema: Compiled strawberry.Schema instance.
        container: rodi DI Container.
        command_bus: Optional CommandBusPort instance.
        query_bus: Optional QueryBusPort instance.
        graphiql: If True, enables the GraphiQL interactive playground.

    Returns:
        Configured strawberry.fastapi.GraphQLRouter instance.

    Raises:
        MissingDependencyError: If fastapi is not installed.
    """
    _require_fastapi()
    from starlette.requests import Request
    from strawberry.fastapi import GraphQLRouter

    async def get_context(request: Request) -> GraphQLContext:
        # Dynamically resolve buses from container if not passed explicitly
        c_bus = command_bus
        if c_bus is None and container is not None:
            try:
                c_bus = container.resolve(CommandBusPort)
            except Exception:  # noqa: BLE001
                c_bus = None

        q_bus = query_bus
        if q_bus is None and container is not None:
            try:
                q_bus = container.resolve(QueryBusPort)
            except Exception:  # noqa: BLE001
                q_bus = None

        ctx = GraphQLContext(
            container=container,
            command_bus=c_bus,
            query_bus=q_bus,
        )
        ctx.request = request
        return ctx

    return GraphQLRouter(
        schema=schema,
        context_getter=get_context,
        graphql_ide="graphiql" if graphiql else None,
    )


def mount_graphql_router(
    app: Any,
    schema: strawberry.Schema,
    container: Container,
    *,
    path: str = "/graphql",
    graphiql: bool = True,
) -> None:
    """Mount Strawberry GraphQL router directly onto a FastAPI application instance.

    Args:
        app: Target FastAPI application instance.
        schema: Compiled strawberry.Schema.
        container: rodi DI Container.
        path: Route prefix for GraphQL endpoints. Defaults to "/graphql".
        graphiql: If True, enables GraphiQL playground.

    Returns:
        None.

    Raises:
        MissingDependencyError: If fastapi is not installed.
    """
    _require_fastapi()
    router = create_graphql_router(
        schema=schema,
        container=container,
        graphiql=graphiql,
    )
    app.include_router(router, prefix=path)


__all__ = [
    "create_graphql_router",
    "mount_graphql_router",
]
