from collections.abc import Callable, Sequence
from typing import Any

import strawberry
from strawberry.extensions import SchemaExtension
from strawberry.types import Info

from hexastack_graphql.domain.context import GraphQLContext
from hexastack_graphql.domain.exceptions import SchemaBuildingError


class GraphQLSchemaRegistry:
    """Registry maintaining registered GraphQL query types, mutation types, and fields.

    Notes/Architectural Intent:
        Aggregates modular GraphQL query and mutation fields registered across
        distributed application modules, compiling them into a unified strawberry.Schema.
    """

    def __init__(self) -> None:
        """Initialize empty schema registry."""
        self._query_types: list[type[Any]] = []
        self._mutation_types: list[type[Any]] = []
        self._query_fields: dict[str, Any] = {}
        self._mutation_fields: dict[str, Any] = {}
        self._custom_schema: strawberry.Schema | None = None

    def _build_query_root(self) -> type[Any]:
        """Assemble composite or fallback GraphQL Query root type."""
        if self._query_types:
            if len(self._query_types) == 1 and not self._query_fields:
                return self._query_types[0]
            bases = tuple(self._query_types)
            fields = dict(self._query_fields)
            QueryType = type("Query", bases, fields)
            return strawberry.type(QueryType)

        if self._query_fields:
            QueryType = type("Query", (), dict(self._query_fields))
            return strawberry.type(QueryType)

        @strawberry.type
        class DefaultQuery:
            @strawberry.field
            def ping(self, info: Info[GraphQLContext, Any]) -> str:
                return "pong"

        return DefaultQuery

    def _build_mutation_root(self) -> type[Any] | None:
        """Assemble composite GraphQL Mutation root type if any mutations registered."""
        if self._mutation_types:
            if len(self._mutation_types) == 1 and not self._mutation_fields:
                return self._mutation_types[0]
            bases = tuple(self._mutation_types)
            MutationType = type("Mutation", bases, dict(self._mutation_fields))
            return strawberry.type(MutationType)

        if self._mutation_fields:
            MutationType = type("Mutation", (), dict(self._mutation_fields))
            return strawberry.type(MutationType)

        return None

    def build_schema(
        self,
        extensions: Sequence[type[SchemaExtension] | Callable[[], SchemaExtension]]
        | None = None,
    ) -> strawberry.Schema:
        """Assemble all registered types and fields into a strawberry.Schema.

        Args:
            extensions: Optional list of strawberry SchemaExtension classes or instances.

        Returns:
            The compiled strawberry.Schema instance.

        Raises:
            SchemaBuildingError: If schema assembly or validation fails.
        """
        if self._custom_schema is not None:
            return self._custom_schema

        query_cls = self._build_query_root()
        mutation_cls = self._build_mutation_root()

        try:
            return strawberry.Schema(
                query=query_cls,
                mutation=mutation_cls,
                extensions=extensions or (),
            )
        except Exception as e:
            raise SchemaBuildingError(f"Failed to build GraphQL schema: {e}") from e

    def clear(self) -> None:
        """Clear all registered schema components (used for test isolation)."""
        self._query_types.clear()
        self._mutation_types.clear()
        self._query_fields.clear()
        self._mutation_fields.clear()
        self._custom_schema = None

    def register_mutation_field(self, name: str, field_def: Any) -> None:
        """Register an individual mutation field or resolver function.

        Args:
            name: Field name.
            field_def: Strawberry field or resolver function.
        """
        self._mutation_fields[name] = field_def

    def register_mutation_type(self, cls: type[Any]) -> None:
        """Register a Strawberry type class containing mutation fields.

        Args:
            cls: A class decorated with @strawberry.type.
        """
        if cls not in self._mutation_types:
            self._mutation_types.append(cls)

    def register_query_field(self, name: str, field_def: Any) -> None:
        """Register an individual query field or resolver function.

        Args:
            name: Field name.
            field_def: Strawberry field or resolver function.
        """
        self._query_fields[name] = field_def

    def register_query_type(self, cls: type[Any]) -> None:
        """Register a Strawberry type class containing query fields.

        Args:
            cls: A class decorated with @strawberry.type.
        """
        if cls not in self._query_types:
            self._query_types.append(cls)

    def set_custom_schema(self, schema: strawberry.Schema) -> None:
        """Explicitly override with a pre-constructed Strawberry Schema.

        Args:
            schema: Pre-configured strawberry.Schema instance.
        """
        self._custom_schema = schema


__all__ = [
    "GraphQLSchemaRegistry",
]
