"""In-memory dictionary adapter implementing TodoRepositoryPort."""

from __future__ import annotations

from todo_app.domain.models import TodoItem
from todo_app.ports.repositories import TodoRepositoryPort


class InMemoryTodoRepository(TodoRepositoryPort):
    """Volatile in-memory dictionary storage for fast unit testing."""

    def __init__(self) -> None:
        """Initialize empty in-memory repository storage."""
        self._storage: dict[str, TodoItem] = {}

    def save(self, item: TodoItem) -> None:
        """Persist or update To-Do entity in memory dictionary."""
        self._storage[item.id] = item

    def get_by_id(self, todo_id: str) -> TodoItem | None:
        """Retrieve To-Do entity by unique id."""
        return self._storage.get(todo_id)

    def list_all(self, completed: bool | None = None) -> list[TodoItem]:
        """List all stored To-Do entities, optionally filtering by completion."""
        items = list(self._storage.values())
        if completed is not None:
            items = [i for i in items if i.completed == completed]
        return items

    def delete(self, todo_id: str) -> bool:
        """Delete To-Do entity from memory storage."""
        if todo_id in self._storage:
            del self._storage[todo_id]
            return True
        return False
