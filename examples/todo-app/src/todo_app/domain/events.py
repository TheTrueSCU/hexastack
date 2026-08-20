"""Domain events emitted during To-Do lifecycle operations.

Notes/Architectural Intent:
    Encapsulates immutable state changes that have occurred within the domain.
    Used for transactional outbox streaming and asynchronous notification dispatch.
"""

from __future__ import annotations

from dataclasses import dataclass
from hexastack_core.domain import Event


@dataclass(frozen=True)
class AdminDeletedUserTodoEvent(Event):
    """Emitted when an Administrator deletes a To-Do item owned by another user."""

    todo_id: str
    todo_title: str
    owner_id: str
    deleted_by: str


__all__ = [
    "AdminDeletedUserTodoEvent",
]
