"""Unit tests verifying pure domain models, business logic, and CQRS handlers."""

import pytest

from todo_app.adapters.driven.database import InMemoryTodoRepository
from todo_app.domain.commands import (
    CompleteTodoCommand,
    CreateTodoCommand,
    DeleteTodoCommand,
    ListTodosQuery,
)
from todo_app.domain.models import (
    Priority,
    TodoAlreadyCompletedError,
    TodoItem,
    TodoNotFoundError,
)
from todo_app.infra.handlers import (
    handle_complete_todo,
    handle_create_todo,
    handle_delete_todo,
    handle_list_todos,
)


@pytest.mark.ch01
@pytest.mark.ch02
@pytest.mark.ch03
@pytest.mark.ch04
def test_todo_item_creation_and_completion():
    """Verify entity initialization and completion transitions."""
    item = TodoItem(title="Write Docs", priority=Priority.HIGH)
    assert item.title == "Write Docs"
    assert item.priority == Priority.HIGH
    assert not item.completed
    assert item.id is not None

    item.mark_completed()
    assert item.completed

    with pytest.raises(TodoAlreadyCompletedError):
        item.mark_completed()


@pytest.mark.ch01
@pytest.mark.ch02
@pytest.mark.ch03
@pytest.mark.ch04
def test_handlers_end_to_end(todo_repo: InMemoryTodoRepository):
    """Verify CQRS handlers perform storage operations through repository port."""
    # 1. Create task
    cmd = CreateTodoCommand(
        title="Ship Release", description="v1.0", priority=Priority.HIGH
    )
    dto = handle_create_todo(cmd, repo=todo_repo)
    assert dto.title == "Ship Release"
    assert dto.priority == Priority.HIGH
    assert not dto.completed

    # 2. List tasks
    query = ListTodosQuery()
    items = handle_list_todos(query, repo=todo_repo)
    assert len(items) == 1
    assert items[0].id == dto.id

    # 3. Complete task
    comp_cmd = CompleteTodoCommand(todo_id=dto.id)
    comp_dto = handle_complete_todo(comp_cmd, repo=todo_repo)
    assert comp_dto.completed

    # 4. Delete task
    del_cmd = DeleteTodoCommand(todo_id=dto.id)
    assert handle_delete_todo(del_cmd, repo=todo_repo)

    # 5. Verify not found
    with pytest.raises(TodoNotFoundError):
        handle_complete_todo(comp_cmd, repo=todo_repo)
