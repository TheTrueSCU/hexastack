from collections.abc import Callable
from typing import Any, cast

import strawberry

from hexastack_graphql.infra.autodiscovery import (
    _GRAPHQL_FIELD_ATTR,
    _GRAPHQL_TYPE_ATTR,
    GraphQLFieldMetadata,
    GraphQLTypeMetadata,
)
from hexastack_graphql.infra.registries.schema import GraphQLSchemaRegistry

_default_registry = GraphQLSchemaRegistry()


__all__ = [
    "get_schema_registry",
    "graphql_mutation",
    "graphql_mutation_type",
    "graphql_query",
    "graphql_query_type",
]


def get_schema_registry() -> GraphQLSchemaRegistry:
    """Return the global default GraphQLSchemaRegistry instance.

    Returns:
        GraphQLSchemaRegistry instance.
    """
    return _default_registry


def graphql_mutation(
    name: str | None = None,
    *,
    description: str | None = None,
) -> Callable[[Callable[..., Any]], Any]:
    """Decorator registering a standalone function as a root GraphQL mutation field.

    Args:
        name: Optional custom field name.
        description: Optional GraphQL documentation description.

    Returns:
        Decorator function.
    """

    def decorator(fn: Callable[..., Any]) -> Any:
        field_name = name or getattr(fn, "__name__", "field")
        s_field = strawberry.mutation(fn, name=field_name, description=description)
        setattr(
            s_field,
            _GRAPHQL_FIELD_ATTR,
            GraphQLFieldMetadata(kind="mutation", name=field_name),
        )
        _default_registry.register_mutation_field(field_name, s_field)
        return s_field

    return decorator


def graphql_mutation_type[T: type[Any]](cls: T) -> T:
    """Decorator registering a class as a root Mutation type.

    Notes/Architectural Intent:
        Automatically applies @strawberry.type if not already applied,
        attaches discovery metadata, and registers in the default schema registry.

    Args:
        cls: Target class containing mutation fields.

    Returns:
        Decorated Strawberry type class.
    """
    wrapped: Any = cls
    if not hasattr(cls, "__strawberry_definition__"):
        wrapped = strawberry.type(cls)
    setattr(wrapped, _GRAPHQL_TYPE_ATTR, GraphQLTypeMetadata(kind="mutation"))
    _default_registry.register_mutation_type(cast("type[Any]", wrapped))
    return cast("T", wrapped)


def graphql_query(
    name: str | None = None,
    *,
    description: str | None = None,
) -> Callable[[Callable[..., Any]], Any]:
    """Decorator registering a standalone function as a root GraphQL query field.

    Args:
        name: Optional custom field name.
        description: Optional GraphQL documentation description.

    Returns:
        Decorator function.
    """

    def decorator(fn: Callable[..., Any]) -> Any:
        field_name = name or getattr(fn, "__name__", "field")
        s_field = strawberry.field(fn, name=field_name, description=description)
        setattr(
            s_field,
            _GRAPHQL_FIELD_ATTR,
            GraphQLFieldMetadata(kind="query", name=field_name),
        )
        _default_registry.register_query_field(field_name, s_field)
        return s_field

    return decorator


def graphql_query_type[T: type[Any]](cls: T) -> T:
    """Decorator registering a class as a root Query type.

    Notes/Architectural Intent:
        Automatically applies @strawberry.type if not already applied,
        attaches discovery metadata, and registers in the default schema registry.

    Args:
        cls: Target class containing query fields.

    Returns:
        Decorated Strawberry type class.
    """
    wrapped: Any = cls
    if not hasattr(cls, "__strawberry_definition__"):
        wrapped = strawberry.type(cls)
    setattr(wrapped, _GRAPHQL_TYPE_ATTR, GraphQLTypeMetadata(kind="query"))
    _default_registry.register_query_type(cast("type[Any]", wrapped))
    return cast("T", wrapped)
