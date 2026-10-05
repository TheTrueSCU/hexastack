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


def test_autodiscover_graphql_fields_and_metadata():
    from hexastack_graphql.infra.autodiscovery import (
        GraphQLFieldMetadata,
        GraphQLTypeMetadata,
        _register_graphql_field,
        _register_graphql_type,
    )
    from hexastack_graphql.infra.decorators import (
        graphql_mutation,
        graphql_query,
    )

    # 1. Metadata constructors
    t_meta = GraphQLTypeMetadata(kind="query")
    assert t_meta.kind == "query"

    f_meta = GraphQLFieldMetadata(kind="mutation", name="custom_mutation_name")
    assert f_meta.kind == "mutation"
    assert f_meta.name == "custom_mutation_name"

    # 2. Field autodiscovery with decorators
    mod = types.ModuleType("dummy_graphql_fields_mod")

    @graphql_query(name="my_named_query")
    def fetch_data() -> str:
        return "data"

    @graphql_mutation()
    def unnamed_mutation() -> bool:
        return True

    setattr(mod, "fetch_data", fetch_data)  # noqa: B010
    setattr(mod, "unnamed_mutation", unnamed_mutation)  # noqa: B010

    reg = GraphQLSchemaRegistry()
    autodiscover_graphql_schema([mod], reg)

    assert "my_named_query" in reg._query_fields
    assert "unnamed_mutation" in reg._mutation_fields

    # 3. Direct helper test with non-metadata object (graceful no-op)
    class PlainClass:
        pass

    def plain_fn():
        pass

    _register_graphql_type(PlainClass, reg)
    _register_graphql_field(plain_fn, reg)


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
    res_reg = autodiscover_graphql_schema([mod], custom_reg)
    assert res_reg is custom_reg

    assert len(custom_reg._query_types) == 1
    assert custom_reg._query_types[0] is ModQuery
    assert len(custom_reg._mutation_types) == 1
    assert custom_reg._mutation_types[0] is ModMutation


def test_autodiscover_graphql_query_and_mutation_branches():
    """Verify autodiscovery of unnamed query field and mutation type branches."""
    from hexastack_graphql.infra.decorators import graphql_mutation_type, graphql_query

    mod = types.ModuleType("dummy_graphql_branches_mod")

    @graphql_query()
    def unnamed_query() -> str:
        return "unnamed"

    @graphql_mutation_type
    class StandaloneMutation:
        pass

    setattr(mod, "unnamed_query", unnamed_query)  # noqa: B010
    setattr(mod, "StandaloneMutation", StandaloneMutation)  # noqa: B010

    reg = GraphQLSchemaRegistry()
    autodiscover_graphql_schema([mod], reg)

    assert "unnamed_query" in reg._query_fields
    assert StandaloneMutation in reg._mutation_types
