"""Abstract repository ports for persisting To-Do entities."""

from abc import ABC, abstractmethod

from todo_app.domain.models import TodoItem


class TodoRepositoryPort(ABC):
    """Secondary (Driven) Port interface for To-Do item persistence."""

    @abstractmethod
    def save(self, item: TodoItem) -> None:
        """Persist or update a To-Do entity."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, todo_id: str) -> TodoItem | None:
        """Fetch a To-Do entity by unique identifier."""
        raise NotImplementedError

    @abstractmethod
    def list_all(self, completed: bool | None = None) -> list[TodoItem]:
        """Fetch all To-Do items, optionally filtered by status."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, todo_id: str) -> bool:
        """Delete a To-Do entity by identifier. Returns True if deleted."""
        raise NotImplementedError
