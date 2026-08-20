"""Driven database repository adapters for To-Do item persistence."""

from __future__ import annotations

from todo_app.domain.models import TodoItem
from todo_app.ports.repositories import TodoRepositoryPort


class InMemoryTodoRepository(TodoRepositoryPort):
    """In-memory dictionary-backed repository adapter for testing and rapid local iteration."""

    def __init__(self) -> None:
        """Initialize in-memory storage dictionary."""
        self._storage: dict[str, TodoItem] = {}

    def save(self, item: TodoItem) -> None:
        """Persist or update To-Do entity in memory."""
        self._storage[item.id] = item

    def get_by_id(self, todo_id: str) -> TodoItem | None:
        """Fetch To-Do entity by identifier from memory."""
        return self._storage.get(todo_id)

    def list_all(self, completed: bool | None = None) -> list[TodoItem]:
        """List all items from memory with optional completion status filter."""
        items = list(self._storage.values())
        if completed is not None:
            return [i for i in items if i.completed is completed]
        return items

    def delete(self, todo_id: str) -> bool:
        """Delete To-Do entity from memory. Returns True if deleted."""
        return self._storage.pop(todo_id, None) is not None
