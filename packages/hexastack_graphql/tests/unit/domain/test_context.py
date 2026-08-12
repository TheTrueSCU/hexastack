from hexastack_graphql.domain.context import GraphQLContext
from hexastack_graphql.domain.exceptions import GraphQLError, SchemaBuildingError
from rodi import Container


def test_graphql_context_creation():
    container = Container()
    ctx = GraphQLContext(container=container, properties={"key": "value"})

    assert ctx.container is container
    assert ctx.command_bus is None
    assert ctx.query_bus is None
    assert ctx.request is None
    assert ctx.properties["key"] == "value"


def test_graphql_exceptions_hierarchy():
    err = SchemaBuildingError("Invalid schema")
    assert isinstance(err, GraphQLError)
    assert str(err) == "Invalid schema"
