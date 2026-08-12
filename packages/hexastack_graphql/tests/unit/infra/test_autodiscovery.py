import types

import strawberry
from hexastack_graphql.infra.autodiscovery import (
    autodiscover_graphql_schema,
)
from hexastack_graphql.infra.decorators import (
    graphql_mutation_type,
    graphql_query_type,
)
from hexastack_graphql.infra.registries.schema import GraphQLSchemaRegistry


def test_autodiscover_graphql_schema():
    mod = types.ModuleType("dummy_graphql_module")

    @graphql_query_type
    class ModQuery:
        @strawberry.field
        def answer(self) -> int:
            return 42

    @graphql_mutation_type
    class ModMutation:
        @strawberry.mutation
        def do_it(self) -> bool:
            return True

    setattr(mod, "ModQuery", ModQuery)  # noqa: B010
    setattr(mod, "ModMutation", ModMutation)  # noqa: B010

    custom_reg = GraphQLSchemaRegistry()
    autodiscover_graphql_schema([mod], custom_reg)

    assert len(custom_reg._query_types) == 1
    assert custom_reg._query_types[0] is ModQuery
    assert len(custom_reg._mutation_types) == 1
    assert custom_reg._mutation_types[0] is ModMutation
