"""Pure domain models and value objects for the To-Do microservice.

Notes/Architectural Intent:
    100% Pure Python with zero framework dependencies (no FastAPI, SQLAlchemy, or HTTP models).
    Enforces domain invariants, entity identity, owner association, and completion transitions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum


class Priority(StrEnum):
    """Urgency priority levels for a To-Do item."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TodoDomainError(Exception):
    """Base domain exception for To-Do operations."""

    pass


class TodoNotFoundError(TodoDomainError):
    """Raised when an operation is attempted on a non-existent To-Do item."""

    def __init__(self, todo_id: str) -> None:
        """Initialize with missing item id."""
        super().__init__(f"To-Do item '{todo_id}' not found.")
        self.todo_id = todo_id


class TodoAlreadyCompletedError(TodoDomainError):
    """Raised when attempting to complete an already completed To-Do item."""

    def __init__(self, todo_id: str) -> None:
        """Initialize with completed item id."""
        super().__init__(f"To-Do item '{todo_id}' is already marked as completed.")
        self.todo_id = todo_id


@dataclass
class TodoItem:
    """Core domain entity representing a task in the To-Do list."""

    title: str
    owner_id: str = "alice"
    description: str = ""
    priority: Priority = Priority.MEDIUM
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    completed: bool = False

    def mark_completed(self) -> None:
        """Transition task state to completed.

        Raises:
            TodoAlreadyCompletedError: If the item was already completed.
        """
        if self.completed:
            raise TodoAlreadyCompletedError(self.id)
        self.completed = True


__all__ = [
    "Priority",
    "TodoAlreadyCompletedError",
    "TodoDomainError",
    "TodoItem",
    "TodoNotFoundError",
]
