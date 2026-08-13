import inspect
from collections.abc import Sequence
from types import ModuleType
from typing import Any

from hexastack_core.infra.autodiscovery import (
    DiscoveryVisitor,
    scan_modules,
)

from hexastack_graphql.infra.registries.schema import GraphQLSchemaRegistry

_GRAPHQL_TYPE_ATTR = "__hexastack_graphql_type__"
_GRAPHQL_FIELD_ATTR = "__hexastack_graphql_field__"


class GraphQLTypeMetadata:
    """Metadata container for decorated GraphQL root types."""

    def __init__(self, kind: str) -> None:
        self.kind = kind  # "query" or "mutation"


class GraphQLFieldMetadata:
    """Metadata container for decorated standalone GraphQL fields."""

    def __init__(self, kind: str, name: str | None = None) -> None:
        self.kind = kind  # "query" or "mutation"
        self.name = name


def create_graphql_visitor(
    registry: GraphQLSchemaRegistry,
) -> DiscoveryVisitor:
    """Create a DiscoveryVisitor callback for single-pass GraphQL schema element discovery.

    Notes/Architectural Intent:
        Inspects discovered classes and functions for GraphQL decorator metadata,
        registering query/mutation types and fields into the supplied schema registry
        during single-pass reflection.

    Args:
        registry: Target GraphQLSchemaRegistry instance.

    Returns:
        DiscoveryVisitor callable accepting (member, module).
    """

    def visitor(obj: Any, module: ModuleType) -> None:
        if inspect.isclass(obj):
            type_meta: GraphQLTypeMetadata | None = getattr(
                obj, _GRAPHQL_TYPE_ATTR, None
            )
            if type_meta is not None:
                if type_meta.kind == "query":
                    registry.register_query_type(obj)
                elif type_meta.kind == "mutation":
                    registry.register_mutation_type(obj)

        field_meta: GraphQLFieldMetadata | None = getattr(
            obj, _GRAPHQL_FIELD_ATTR, None
        )
        if field_meta is not None:
            field_name = field_meta.name or getattr(obj, "__name__", "field")
            if field_meta.kind == "query":
                registry.register_query_field(field_name, obj)
            elif field_meta.kind == "mutation":
                registry.register_mutation_field(field_name, obj)

    return visitor


def autodiscover_graphql_schema(
    packages_to_scan: Sequence[str | ModuleType],
    registry: GraphQLSchemaRegistry,
) -> GraphQLSchemaRegistry:
    """Discover decorated GraphQL components and register them into the schema registry.

    Args:
        packages_to_scan: Sequence of package names or module objects to inspect.
        registry: Target GraphQLSchemaRegistry instance.

    Returns:
        The populated GraphQLSchemaRegistry instance.
    """
    visitor = create_graphql_visitor(registry)
    scan_modules(packages_to_scan, [visitor])
    return registry


__all__ = [
    "GraphQLFieldMetadata",
    "GraphQLTypeMetadata",
    "autodiscover_graphql_schema",
    "create_graphql_visitor",
]
