"""Hexastack bootstrapper and application kernel assembly."""

from hexastack_core.infra.bootstrap import BootstrapResult, bootstrap
from hexastack_cqrs.infra.decorators import command_handler, query_handler

import todo_app.adapters.driving.cli
import todo_app.adapters.driving.http
from todo_app.adapters.driven.database import InMemoryTodoRepository
from todo_app.domain.commands import (
    CompleteTodoCommand,
    CreateTodoCommand,
    DeleteTodoCommand,
    GetTodoQuery,
    ListTodosQuery,
)
from todo_app.infra.handlers import (
    handle_complete_todo,
    handle_create_todo,
    handle_delete_todo,
    handle_get_todo,
    handle_list_todos,
)
from todo_app.ports.repositories import TodoRepositoryPort

# Register CQRS Handlers
command_handler(CreateTodoCommand)(handle_create_todo)
command_handler(CompleteTodoCommand)(handle_complete_todo)
command_handler(DeleteTodoCommand)(handle_delete_todo)
query_handler(ListTodosQuery)(handle_list_todos)
query_handler(GetTodoQuery)(handle_get_todo)


def create_app() -> BootstrapResult:
    """Bootstrap full Hexastack microservice kernel."""
    result = bootstrap(
        packages_to_scan=[
            todo_app.adapters.driving.cli,
            todo_app.adapters.driving.http,
            todo_app.infra.bootstrap,
        ],
    )
    repo = InMemoryTodoRepository()
    result.container.add_instance(repo, declared_class=TodoRepositoryPort)
    return result
