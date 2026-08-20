"""CQRS Command and Query handlers executing domain operations with injected ports."""

from __future__ import annotations

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


def handle_create_todo(cmd: CreateTodoCommand, repo: TodoRepositoryPort) -> TodoItemDTO:
    """Handler creating a new To-Do item and saving via repository port."""
    item = TodoItem(
        title=cmd.title,
        description=cmd.description,
        priority=cmd.priority,
    )
    repo.save(item)
    return _to_dto(item)


def handle_complete_todo(
    cmd: CompleteTodoCommand, repo: TodoRepositoryPort
) -> TodoItemDTO:
    """Handler marking a To-Do item as completed."""
    item = repo.get_by_id(cmd.todo_id)
    if item is None:
        raise TodoNotFoundError(cmd.todo_id)
    item.mark_completed()
    repo.save(item)
    return _to_dto(item)


def handle_delete_todo(cmd: DeleteTodoCommand, repo: TodoRepositoryPort) -> bool:
    """Handler deleting a To-Do item."""
    deleted = repo.delete(cmd.todo_id)
    if not deleted:
        raise TodoNotFoundError(cmd.todo_id)
    return True


def handle_list_todos(
    query: ListTodosQuery, repo: TodoRepositoryPort
) -> list[TodoItemDTO]:
    """Handler querying To-Do items from repository."""
    items = repo.list_all(completed=query.completed_only)
    return [_to_dto(i) for i in items]


def handle_get_todo(query: GetTodoQuery, repo: TodoRepositoryPort) -> TodoItemDTO:
    """Handler fetching single To-Do item."""
    item = repo.get_by_id(query.todo_id)
    if item is None:
        raise TodoNotFoundError(query.todo_id)
    return _to_dto(item)
