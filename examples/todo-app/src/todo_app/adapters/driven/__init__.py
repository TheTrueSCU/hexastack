"""Driven (outbound) infrastructure adapters."""

from todo_app.adapters.driven.database import InMemoryTodoRepository

__all__ = [
    "InMemoryTodoRepository",
]
