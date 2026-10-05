"""gRPC Protocol Adapter for To-Do Service using @proto_schema inline contracts."""

from __future__ import annotations

from dataclasses import dataclass

from hexastack_grpc.infra.decorators import proto_schema


@proto_schema(
    schema="""
    syntax = "proto3";
    package todo.v1;

    message CreateTodoRequest {
        string title = 1;
        string description = 2;
        string priority = 3;
    }

    message CreateTodoResponse {
        string id = 1;
        string title = 2;
        string status = 3;
    }

    service TodoService {
        rpc CreateTodo (CreateTodoRequest) returns (CreateTodoResponse);
    }
    """,
    message_name="CreateTodoRequest",
    service_name="todo.v1.TodoService",
    rpc_name="CreateTodo",
)
@dataclass
class CreateTodoRpcCommand:
    """gRPC Inbound Command contract."""

    title: str
    description: str = ""
    priority: str = "medium"
