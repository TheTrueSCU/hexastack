"""FastAPI REST routing adapters exposing CQRS commands and queries."""

from hexastack_fastapi.infra.decorators import api_command, api_query

from todo_app.domain.commands import (
    CompleteTodoCommand,
    CreateTodoCommand,
    DeleteTodoCommand,
    GetTodoQuery,
    ListTodosQuery,
)

# Expose CQRS operations as HTTP REST endpoints
api_command(
    "/todos",
    method="POST",
    summary="Create a new To-Do task",
    status_code=201,
)(CreateTodoCommand)

api_command(
    "/todos/{todo_id}/complete",
    method="POST",
    summary="Mark a To-Do task as completed",
)(CompleteTodoCommand)

api_command(
    "/todos/{todo_id}",
    method="DELETE",
    summary="Delete a To-Do task",
)(DeleteTodoCommand)

api_query(
    "/todos",
    summary="List all To-Do tasks",
)(ListTodosQuery)

api_query(
    "/todos/{todo_id}",
    summary="Get single To-Do task details",
)(GetTodoQuery)
