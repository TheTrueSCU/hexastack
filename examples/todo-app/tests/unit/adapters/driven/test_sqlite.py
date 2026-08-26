"""Unit and integration tests for Chapter 2 SQLite repository adapter."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from todo_app.adapters.driven.sqlite import (
    SqliteTodoRepository,
    create_sqlite_session_factory,
)
from todo_app.domain.models import Priority, TodoItem
from todo_app.entrypoints.ch02_sqlite import build_app


@pytest.mark.ch02
def test_sqlite_repository_crud():
    """Verify CRUD lifecycle of SqliteTodoRepository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        factory = create_sqlite_session_factory(f"sqlite:///{db_path}")
        repo = SqliteTodoRepository(factory)

        item = TodoItem(
            id="todo-1",
            title="Buy groceries",
            description="Milk, bread",
            priority=Priority.HIGH,
            completed=False,
        )

        # 1. Save
        repo.save(item)

        # 2. Get by ID
        fetched = repo.get_by_id("todo-1")
        assert fetched is not None
        assert fetched.title == "Buy groceries"
        assert fetched.priority == Priority.HIGH

        # 3. List
        items = repo.list_all(completed=False)
        assert len(items) == 1

        # 4. Update
        item.completed = True
        repo.save(item)
        updated = repo.get_by_id("todo-1")
        assert updated is not None
        assert updated.completed is True
        assert len(repo.list_all(completed=False)) == 0

        # 5. Delete
        assert repo.delete("todo-1") is True
        assert repo.get_by_id("todo-1") is None


@pytest.mark.ch02
def test_ch02_sqlite_fastapi_integration():
    """Verify Chapter 2 FastAPI entrypoint executes with persistent SQLite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "api_test.db"
        app = build_app(db_url=f"sqlite:///{db_path}")
        client = TestClient(app)

        # Create todo via HTTP
        resp = client.post("/todos", json={"title": "Write Chapter 2 Docs", "priority": "high"})
        assert resp.status_code == 201
        created_id = resp.json()["id"]

        # Retrieve todo via HTTP
        get_resp = client.get(f"/todos/{created_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == "Write Chapter 2 Docs"
