"""Shared pytest fixtures for the To-Do test suite."""

import pytest

from todo_app.adapters.driven.database import InMemoryTodoRepository


@pytest.fixture
def todo_repo() -> InMemoryTodoRepository:
    """Provide a fresh isolated InMemoryTodoRepository for each test."""
    return InMemoryTodoRepository()
