from typing import Any

import strawberry
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

    def register_query_type(self, cls: type[Any]) -> None:
        """Register a Strawberry type class containing query fields.

        Args:
            cls: A class decorated with @strawberry.type.
        """
        if cls not in self._query_types:
            self._query_types.append(cls)

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

    def register_mutation_field(self, name: str, field_def: Any) -> None:
        """Register an individual mutation field or resolver function.

        Args:
            name: Field name.
            field_def: Strawberry field or resolver function.
        """
        self._mutation_fields[name] = field_def

    def set_custom_schema(self, schema: strawberry.Schema) -> None:
        """Explicitly override with a pre-constructed Strawberry Schema.

        Args:
            schema: Pre-configured strawberry.Schema instance.
        """
        self._custom_schema = schema

    def build_schema(
        self,
        extensions: list[Any] | None = None,
    ) -> strawberry.Schema:
        """Compile all registered types and fields into a Strawberry Schema.

        Notes/Architectural Intent:
            If a custom schema was registered, returns it directly. Otherwise,
            synthesizes root Query and Mutation types from registered classes
            and field definitions.

        Args:
            extensions: Optional list of Strawberry SchemaExtension instances.

        Returns:
            Compiled strawberry.Schema instance.

        Raises:
            SchemaBuildingError: If schema compilation fails.
        """
        if self._custom_schema is not None:
            return self._custom_schema

        # 1. Assemble Query Root
        query_cls: type[Any]
        if self._query_types:
            # If multiple query classes registered, create a composite inheriting from them
            if len(self._query_types) == 1 and not self._query_fields:
                query_cls = self._query_types[0]
            else:
                bases = tuple(self._query_types)
                fields = dict(self._query_fields)

                # If no fields and bases, provide ping
                if not fields and not bases:

                    @strawberry.field
                    def ping(info: Info[GraphQLContext, Any]) -> str:
                        return "pong"

                    fields["ping"] = ping

                composite_dict = dict(fields)
                QueryType = type("Query", bases, composite_dict)
                query_cls = strawberry.type(QueryType)
        elif self._query_fields:
            composite_dict = dict(self._query_fields)
            QueryType = type("Query", (), composite_dict)
            query_cls = strawberry.type(QueryType)
        else:
            # Default fallback query root
            @strawberry.type
            class DefaultQuery:
                @strawberry.field
                def ping(self, info: Info[GraphQLContext, Any]) -> str:
                    return "pong"

            query_cls = DefaultQuery

        # 2. Assemble Mutation Root (if any registered)
        mutation_cls: type[Any] | None = None
        if self._mutation_types:
            if len(self._mutation_types) == 1 and not self._mutation_fields:
                mutation_cls = self._mutation_types[0]
            else:
                bases = tuple(self._mutation_types)
                composite_dict = dict(self._mutation_fields)
                MutationType = type("Mutation", bases, composite_dict)
                mutation_cls = strawberry.type(MutationType)
        elif self._mutation_fields:
            composite_dict = dict(self._mutation_fields)
            MutationType = type("Mutation", (), composite_dict)
            mutation_cls = strawberry.type(MutationType)

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


__all__ = [
    "GraphQLSchemaRegistry",
]
