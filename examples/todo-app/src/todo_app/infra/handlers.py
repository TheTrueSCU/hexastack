"""CQRS Command and Query handlers executing domain operations with injected ports."""

from __future__ import annotations

from hexastack_cqrs.infra.decorators import command_handler, query_handler
from todo_app.domain.commands import (
    CompleteTodoCommand,
    CreateTodoCommand,
    DeleteTodoCommand,
    GetTodoQuery,
    ListTodosQuery,
    TodoItemDTO,
)
from todo_app.domain.models import TodoItem, TodoNotFoundError
from todo_app.ports.repositories import TodoRepositoryPort


def _to_dto(item: TodoItem) -> TodoItemDTO:
    return TodoItemDTO(
        id=item.id,
        title=item.title,
        description=item.description,
        priority=item.priority,
        completed=item.completed,
    )


@command_handler(CreateTodoCommand)
class CreateTodoHandler:
    """Handler creating a new To-Do item and saving via repository port."""

    def __init__(self, repo: TodoRepositoryPort) -> None:
        self.repo = repo

    def __call__(self, cmd: CreateTodoCommand) -> TodoItemDTO:
        item = TodoItem(
            title=cmd.title,
            description=cmd.description,
            priority=cmd.priority,
        )
        self.repo.save(item)
        return _to_dto(item)


@command_handler(CompleteTodoCommand)
class CompleteTodoHandler:
    """Handler marking a To-Do item as completed."""

    def __init__(self, repo: TodoRepositoryPort) -> None:
        self.repo = repo

    def __call__(self, cmd: CompleteTodoCommand) -> TodoItemDTO:
        item = self.repo.get_by_id(cmd.todo_id)
        if item is None:
            raise TodoNotFoundError(cmd.todo_id)
        item.mark_completed()
        self.repo.save(item)
        return _to_dto(item)


@command_handler(DeleteTodoCommand)
class DeleteTodoHandler:
    """Handler deleting a To-Do item."""

    def __init__(self, repo: TodoRepositoryPort) -> None:
        self.repo = repo

    def __call__(self, cmd: DeleteTodoCommand) -> bool:
        deleted = self.repo.delete(cmd.todo_id)
        if not deleted:
            raise TodoNotFoundError(cmd.todo_id)
        return True


@query_handler(ListTodosQuery)
class ListTodosHandler:
    """Handler querying To-Do items from repository."""

    def __init__(self, repo: TodoRepositoryPort) -> None:
        self.repo = repo

    def __call__(self, query: ListTodosQuery) -> list[TodoItemDTO]:
        items = self.repo.list_all(completed=query.completed_only)
        return [_to_dto(i) for i in items]


@query_handler(GetTodoQuery)
class GetTodoHandler:
    """Handler fetching single To-Do item."""

    def __init__(self, repo: TodoRepositoryPort) -> None:
        self.repo = repo

    def __call__(self, query: GetTodoQuery) -> TodoItemDTO:
        item = self.repo.get_by_id(query.todo_id)
        if item is None:
            raise TodoNotFoundError(query.todo_id)
        return _to_dto(item)


# Functional helpers for direct unit testing without DI container
def handle_create_todo(cmd: CreateTodoCommand, repo: TodoRepositoryPort) -> TodoItemDTO:
    return CreateTodoHandler(repo)(cmd)


def handle_complete_todo(cmd: CompleteTodoCommand, repo: TodoRepositoryPort) -> TodoItemDTO:
    return CompleteTodoHandler(repo)(cmd)


def handle_delete_todo(cmd: DeleteTodoCommand, repo: TodoRepositoryPort) -> bool:
    return DeleteTodoHandler(repo)(cmd)


def handle_list_todos(query: ListTodosQuery, repo: TodoRepositoryPort) -> list[TodoItemDTO]:
    return ListTodosHandler(repo)(query)


def handle_get_todo(query: GetTodoQuery, repo: TodoRepositoryPort) -> TodoItemDTO:
    return GetTodoHandler(repo)(query)
