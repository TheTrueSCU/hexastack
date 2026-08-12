from typing import Any, Protocol

from hexastack_graphql.domain.context import GraphQLContext


class GraphQLContextFactoryPort(Protocol):
    """Protocol for creating a GraphQLContext per execution or request.

    Notes/Architectural Intent:
        Allows custom presentation adapters or middleware to customize context
        construction (e.g. extracting auth headers, per-request DB sessions).
    """

    def __call__(self, request: Any | None = None) -> GraphQLContext:
        """Construct and return a configured GraphQLContext instance.

        Args:
            request: Optional underlying HTTP/WS request object.

        Returns:
            Configured GraphQLContext instance.
        """
        ...


__all__ = [
    "GraphQLContextFactoryPort",
]
