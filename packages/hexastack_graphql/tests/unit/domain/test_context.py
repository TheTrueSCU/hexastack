from rodi import Container

from hexastack_graphql.domain.context import GraphQLContext


def test_graphql_context_creation():
    container = Container()
    ctx = GraphQLContext(container=container, properties={"key": "value"})

    assert ctx.container is container
    assert ctx.command_bus is None
    assert ctx.query_bus is None
    assert ctx.request is None
    assert ctx.properties == {"key": "value"}


def test_graphql_context_full_fields():
    container = Container()
    mock_cmd_bus = object()
    mock_qry_bus = object()
    mock_req = object()

    ctx = GraphQLContext(
        container=container,
        command_bus=mock_cmd_bus,
        query_bus=mock_qry_bus,
        request=mock_req,
        properties={"env": "production", "user": "alice"},
    )

    assert ctx.container is container
    assert ctx.command_bus is mock_cmd_bus
    assert ctx.query_bus is mock_qry_bus
    assert ctx.request is mock_req
    assert ctx.properties["env"] == "production"
    assert ctx.properties["user"] == "alice"
