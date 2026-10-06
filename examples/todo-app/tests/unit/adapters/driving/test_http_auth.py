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
        status_code = del_resp.status_code
        assert status_code == 200
        del_json = del_resp.json()
        assert del_json == {"deleted": True}


@pytest.mark.ch03
def test_unauthorized_admin_claim_forbidden() -> None:
    """Verify arbitrary callers cannot claim admin access via Bearer token."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "auth_test.db"
        app = build_app(db_url=f"sqlite:///{db_path}")
        client = TestClient(app)

        attacker_headers = {"Authorization": "Bearer admin:attacker"}
        resp = client.get("/todos", headers=attacker_headers)
        status_code = resp.status_code
        assert status_code == 403
        body = resp.json()
        detail = body.get("detail", "")
        assert "Invalid admin credentials" in detail


@pytest.mark.ch03
def test_user_cannot_complete_another_users_todo() -> None:
    """Verify non-owner users cannot mark another user's task as completed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "auth_test.db"
        app = build_app(db_url=f"sqlite:///{db_path}")
        client = TestClient(app)

        # Alice creates a task
        alice_headers = {"Authorization": "Bearer user:alice"}
        resp = client.post(
            "/todos",
            json={"title": "Alice's Project", "priority": "high"},
            headers=alice_headers,
        )
        status_code = resp.status_code
        assert status_code == 201
        todo_id = resp.json()["id"]

        # Bob attempts to complete Alice's task -> 403 Forbidden
        bob_headers = {"Authorization": "Bearer user:bob"}
        comp_resp = client.post(f"/todos/{todo_id}/complete", headers=bob_headers)
        comp_status = comp_resp.status_code
        assert comp_status == 403
        body = comp_resp.json()
        error_msg = body.get("error", body.get("detail", ""))
        assert "Forbidden" in error_msg

        # Alice successfully completes her own task -> 200 OK
        alice_comp = client.post(f"/todos/{todo_id}/complete", headers=alice_headers)
        alice_status = alice_comp.status_code
        assert alice_status == 200
        completed_flag = alice_comp.json()["completed"]
        assert completed_flag is True


@pytest.mark.ch03
def test_admin_can_complete_any_users_todo() -> None:
    """Verify verified admin can mark any user's task as completed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "auth_test.db"
        app = build_app(db_url=f"sqlite:///{db_path}")
        client = TestClient(app)

        # Alice creates a task
        alice_headers = {"Authorization": "Bearer user:alice"}
        resp = client.post(
            "/todos",
            json={"title": "Pending Review", "priority": "medium"},
            headers=alice_headers,
        )
        status_code = resp.status_code
        assert status_code == 201
        todo_id = resp.json()["id"]

        # Admin completes Alice's task -> 200 OK
        admin_headers = {"Authorization": "Bearer admin:superadmin"}
        comp_resp = client.post(f"/todos/{todo_id}/complete", headers=admin_headers)
        comp_status = comp_resp.status_code
        assert comp_status == 200
        completed_flag = comp_resp.json()["completed"]
        assert completed_flag is True


@pytest.mark.ch03
def test_anonymous_cannot_access_or_modify_alices_todo() -> None:
    """Verify unauthenticated requests cannot view, complete, or delete Alice's tasks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "auth_test.db"
        app = build_app(db_url=f"sqlite:///{db_path}")
        client = TestClient(app)

        alice_headers = {"Authorization": "Bearer user:alice"}
        resp = client.post(
            "/todos",
            json={"title": "Alice Confidential", "priority": "high"},
            headers=alice_headers,
        )
        assert resp.status_code == 201
        todo_id = resp.json()["id"]

        # Anonymous cannot read Alice's task
        anon_get = client.get(f"/todos/{todo_id}")
        assert anon_get.status_code == 403

        # Anonymous cannot complete Alice's task
        anon_comp = client.post(f"/todos/{todo_id}/complete")
        assert anon_comp.status_code == 403

        # Anonymous cannot delete Alice's task
        anon_del = client.delete(f"/todos/{todo_id}")
        assert anon_del.status_code == 403


@pytest.mark.ch03
def test_user_cannot_spoof_task_ownership() -> None:
    """Verify non-admin caller cannot claim another user's identity as owner."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "auth_test.db"
        app = build_app(db_url=f"sqlite:///{db_path}")
        client = TestClient(app)

        alice_headers = {"Authorization": "Bearer user:alice"}
        resp = client.post(
            "/todos",
            json={"title": "Spoofed Task", "owner_id": "bob", "priority": "low"},
            headers=alice_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["owner_id"] == "alice"
