from dataclasses import dataclass, field
from typing import Any

from hexastack_cqrs.ports.buses import CommandBusPort, QueryBusPort
from rodi import Container
from strawberry.fastapi.context import BaseContext


@dataclass
class GraphQLContext(BaseContext):
    """Execution context injected into Strawberry GraphQL resolvers.

    Notes/Architectural Intent:
        Carries the rodi DI container and CQRS command/query buses into
        field resolvers, enabling clean dispatching from GraphQL queries
        and mutations. Inherits from Strawberry's BaseContext for full
        FastAPI router integration.
    """

    container: Container | None = None
    command_bus: CommandBusPort | None = None
    query_bus: QueryBusPort | None = None
    request: Any | None = None
    properties: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "GraphQLContext",
]
