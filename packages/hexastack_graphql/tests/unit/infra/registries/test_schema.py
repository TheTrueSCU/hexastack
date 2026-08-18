import strawberry

from hexastack_graphql.infra.decorators import (
    get_schema_registry,
    graphql_mutation_type,
    graphql_query_type,
)
from hexastack_graphql.infra.registries.schema import GraphQLSchemaRegistry


def test_empty_registry_builds_default_ping_schema():
    reg = GraphQLSchemaRegistry()
    schema = reg.build_schema()
    assert isinstance(schema, strawberry.Schema)
    res = schema.execute_sync("{ ping }")
    assert res.data == {"ping": "pong"}


def test_schema_registry_with_custom_schema():
    reg = GraphQLSchemaRegistry()

    @strawberry.type
    class CustomQuery:
        @strawberry.field
        def custom(self) -> str:
            return "custom_val"

    custom_schema = strawberry.Schema(query=CustomQuery)
    reg.set_custom_schema(custom_schema)

    schema = reg.build_schema()
    assert schema is custom_schema
    res = schema.execute_sync("{ custom }")
    assert res.data == {"custom": "custom_val"}


def test_schema_registry_with_query_and_mutation():
    reg = get_schema_registry()

    @graphql_query_type
    class QueryRoot:
        @strawberry.field
        def hello(self, name: str = "World") -> str:
            return f"Hello, {name}!"

    @graphql_mutation_type
    class MutationRoot:
        @strawberry.mutation
        def add(self, a: int, b: int) -> int:
            return a + b

    schema = reg.build_schema()
    res_q = schema.execute_sync('{ hello(name: "Hexastack") }')
    assert res_q.data == {"hello": "Hello, Hexastack!"}

    res_m = schema.execute_sync("mutation { add(a: 2, b: 3) }")
    assert res_m.data == {"add": 5}
