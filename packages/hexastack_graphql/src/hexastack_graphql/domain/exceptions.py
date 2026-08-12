from hexastack_core.domain.exceptions import HexastackError


class GraphQLError(HexastackError):
    """Base exception for all GraphQL adapter errors.

    Notes/Architectural Intent:
        Inherits from HexastackError to maintain unified exception hierarchy
        across core and adapter layers.
    """


class SchemaBuildingError(GraphQLError):
    """Exception raised when GraphQL schema construction or validation fails.

    Notes/Architectural Intent:
        Raised when no queries or mutations are registered, or when invalid
        field definitions conflict during schema compilation.
    """


__all__ = [
    "GraphQLError",
    "SchemaBuildingError",
]
