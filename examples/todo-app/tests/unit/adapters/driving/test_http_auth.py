"""Unit and integration tests for Chapter 3 Auth & RBAC security rules."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from todo_app.entrypoints.ch03_secure import build_app


@pytest.mark.ch03
def test_user_can_create_and_delete_own_todo() -> None:
    """Verify Alice can create and delete her own tasks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "auth_test.db"
        app = build_app(db_url=f"sqlite:///{db_path}")
        client = TestClient(app)

        # Alice creates a task
        alice_headers = {"Authorization": "Bearer user:alice"}
        resp = client.post(
            "/todos",
            json={"title": "Alice's Secret Project", "priority": "high"},
            headers=alice_headers,
        )
        assert resp.status_code == 201
        todo_id = resp.json()["id"]
        assert resp.json()["owner_id"] == "alice"

        # Alice successfully deletes her own task
        del_resp = client.delete(f"/todos/{todo_id}", headers=alice_headers)
        assert del_resp.status_code == 200
        assert del_resp.json() == {"deleted": True}


@pytest.mark.ch03
def test_bob_cannot_delete_alices_todo() -> None:
    """Verify Bob is forbidden from deleting Alice's task."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "auth_test.db"
        app = build_app(db_url=f"sqlite:///{db_path}")
        client = TestClient(app)

        # Alice creates a task
        alice_headers = {"Authorization": "Bearer user:alice"}
        resp = client.post(
            "/todos",
            json={"title": "Alice's Budget Proposal", "priority": "high"},
            headers=alice_headers,
        )
        assert resp.status_code == 201
        todo_id = resp.json()["id"]

        # Bob attempts to delete Alice's task -> 403 Forbidden
        bob_headers = {"Authorization": "Bearer user:bob"}
        del_resp = client.delete(f"/todos/{todo_id}", headers=bob_headers)
        assert del_resp.status_code == 403
        body = del_resp.json()
        assert "Forbidden" in body.get("error", body.get("detail", ""))


@pytest.mark.ch03
def test_admin_can_delete_any_users_todo() -> None:
    """Verify Admin with admin role can delete any user's task."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "auth_test.db"
        app = build_app(db_url=f"sqlite:///{db_path}")
        client = TestClient(app)

        # Alice creates a task
        alice_headers = {"Authorization": "Bearer user:alice"}
        resp = client.post(
            "/todos",
            json={"title": "Stale Task", "priority": "low"},
            headers=alice_headers,
        )
        assert resp.status_code == 201
        todo_id = resp.json()["id"]

        # Admin deletes Alice's task -> 200 OK
        admin_headers = {"Authorization": "Bearer admin:superadmin"}
        del_resp = client.delete(f"/todos/{todo_id}", headers=admin_headers)
        assert del_resp.status_code == 200
        assert del_resp.json() == {"deleted": True}
