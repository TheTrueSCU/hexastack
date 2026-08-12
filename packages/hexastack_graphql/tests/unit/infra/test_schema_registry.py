import pytest
import strawberry
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


def test_empty_registry_builds_default_ping_schema():
    reg = GraphQLSchemaRegistry()
    schema = reg.build_schema()
    result = schema.execute_sync("{ ping }")
    assert result.errors is None
    assert result.data == {"ping": "pong"}


def test_custom_query_type_registration():
    reg = GraphQLSchemaRegistry()

    @strawberry.type
    class UserQuery:
        @strawberry.field
        def hello(self, name: str = "World") -> str:
            return f"Hello, {name}!"

    reg.register_query_type(UserQuery)
    schema = reg.build_schema()

    result = schema.execute_sync('{ hello(name: "Hexastack") }')
    assert result.errors is None
    assert result.data == {"hello": "Hello, Hexastack!"}


def test_custom_mutation_type_registration():
    reg = GraphQLSchemaRegistry()

    @strawberry.type
    class Mutation:
        @strawberry.mutation
        def create_user(self, username: str) -> str:
            return f"User {username} created"

    reg.register_mutation_type(Mutation)
    schema = reg.build_schema()

    result = schema.execute_sync('mutation { createUser(username: "alice") }')
    assert result.errors is None
    assert result.data == {"createUser": "User alice created"}


def test_decorators_registration():
    @graphql_query_type
    class MyQuery:
        @strawberry.field
        def message(self) -> str:
            return "from query decorator"

    @graphql_mutation_type
    class MyMutation:
        @strawberry.mutation
        def send(self, text: str) -> str:
            return f"sent: {text}"

    schema = get_schema_registry().build_schema()

    q_res = schema.execute_sync("{ message }")
    assert q_res.data == {"message": "from query decorator"}

    m_res = schema.execute_sync('mutation { send(text: "hi") }')
    assert m_res.data == {"send": "sent: hi"}
