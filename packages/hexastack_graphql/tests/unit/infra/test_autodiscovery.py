import types

import pytest
import strawberry
from hexastack_graphql.infra.autodiscovery import (
    autodiscover_graphql_schema,
)
from hexastack_graphql.infra.decorators import (
    get_schema_registry,
    graphql_mutation_type,
    graphql_query_type,
)
from hexastack_graphql.infra.registries.schema import GraphQLSchemaRegistry


@pytest.fixture(autouse=True)
def clean_registry():
    reg = get_schema_registry()
    reg.clear()
    yield
    reg.clear()


def test_autodiscover_graphql_schema_from_module():
    mod = types.ModuleType("dummy_gql_mod")

    @graphql_query_type
    class DummyQuery:
        @strawberry.field
        def answer(self) -> int:
            return 42

    @graphql_mutation_type
    class DummyMutation:
        @strawberry.mutation
        def set_answer(self, value: int) -> int:
            return value

    setattr(mod, "DummyQuery", DummyQuery)  # noqa: B010
    setattr(mod, "DummyMutation", DummyMutation)  # noqa: B010

    custom_reg = GraphQLSchemaRegistry()
    autodiscover_graphql_schema([mod], custom_reg)

    schema = custom_reg.build_schema()
    q_res = schema.execute_sync("{ answer }")
    assert q_res.data == {"answer": 42}

    m_res = schema.execute_sync("mutation { setAnswer(value: 100) }")
    assert m_res.data == {"setAnswer": 100}
