"""Unit tests for Chapter 7 gRPC driving adapter and proto schema registration."""

from hexastack_grpc.infra.registries.proto import get_proto_registry

from todo_app.adapters.driving.grpc import CreateTodoRpcCommand


def test_grpc_proto_schema_registered():
    """Verify that CreateTodoRpcCommand registers its inline @proto_schema contract."""
    assert CreateTodoRpcCommand is not None
    registry = get_proto_registry()
    matches = [e for e in registry.entries if e.message_name == "CreateTodoRequest"]

    assert len(matches) > 0
    entry = matches[0]
    assert entry.message_name == "CreateTodoRequest"
    assert entry.service_name == "todo.v1.TodoService"
    assert entry.rpc_name == "CreateTodo"
    assert "package todo.v1;" in (entry.schema or "")
