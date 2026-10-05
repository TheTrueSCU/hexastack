import strawberry
from strawberry.types import Info

from hexastack_graphql.domain.context import GraphQLContext
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


def test_schema_building_error_handling(monkeypatch):
    import pytest

    from hexastack_graphql.domain.exceptions import SchemaBuildingError

    reg = GraphQLSchemaRegistry()

    def bad_schema(*args, **kwargs):
        raise ValueError("Invalid schema config")

    monkeypatch.setattr(strawberry, "Schema", bad_schema)
    with pytest.raises(SchemaBuildingError, match="Failed to build GraphQL schema"):
        reg.build_schema()


def test_schema_registry_clear():
    reg = GraphQLSchemaRegistry()

    @strawberry.type
    class Q:
        @strawberry.field
        def val(self) -> int:
            return 10

    reg.register_query_type(Q)
    reg.clear()
    schema = reg.build_schema()
    res = schema.execute_sync("{ ping }")
    assert res.data == {"ping": "pong"}


def test_schema_registry_composite_with_extra_fields():
    reg = GraphQLSchemaRegistry()

    @strawberry.type
    class BaseQ:
        @strawberry.field
        def base(self) -> str:
            return "base"

    @strawberry.field
    def extra(info: Info[GraphQLContext, None]) -> str:
        return "extra"

    reg.register_query_type(BaseQ)
    reg.register_query_field("extra", extra)

    schema = reg.build_schema()
    res = schema.execute_sync("{ base extra }")
    assert res.data == {"base": "base", "extra": "extra"}


def test_schema_registry_individual_fields():
    reg = GraphQLSchemaRegistry()

    @strawberry.field
    def get_version(info: Info[GraphQLContext, None]) -> str:
        return "1.0.0"

    @strawberry.mutation
    def reset_system(info: Info[GraphQLContext, None]) -> bool:
        return True

    reg.register_query_field("version", get_version)
    reg.register_mutation_field("reset", reset_system)

    schema = reg.build_schema()
    res_q = schema.execute_sync("{ version }")
    assert res_q.data == {"version": "1.0.0"}

    res_m = schema.execute_sync("mutation { reset }")
    assert res_m.data == {"reset": True}


def test_schema_registry_multiple_query_and_mutation_types():
    reg = GraphQLSchemaRegistry()

    @strawberry.type
    class UserQuery:
        @strawberry.field
        def user_name(self) -> str:
            return "Alice"

    @strawberry.type
    class OrderQuery:
        @strawberry.field
        def order_id(self) -> str:
            return "ord-123"

    @strawberry.type
    class UserMutation:
        @strawberry.mutation
        def create_user(self) -> str:
            return "user_created"

    @strawberry.type
    class OrderMutation:
        @strawberry.mutation
        def create_order(self) -> str:
            return "order_created"

    reg.register_query_type(UserQuery)
    reg.register_query_type(OrderQuery)
    reg.register_query_type(UserQuery)  # Deduplicate test

    reg.register_mutation_type(UserMutation)
    reg.register_mutation_type(OrderMutation)
    reg.register_mutation_type(UserMutation)  # Deduplicate test

    schema = reg.build_schema()
    res_q = schema.execute_sync("{ userName orderId }")
    assert res_q.data == {"userName": "Alice", "orderId": "ord-123"}

    res_m = schema.execute_sync("mutation { createUser createOrder }")
    assert res_m.data == {"createUser": "user_created", "createOrder": "order_created"}


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
    reg.clear()

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
