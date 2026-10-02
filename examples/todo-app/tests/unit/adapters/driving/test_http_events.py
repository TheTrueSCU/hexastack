"""Unit and integration tests for Chapter 4 Event-Driven Notifications."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from hexastack_core.adapters.notification import InMemoryNotificationAdapter
from hexastack_core.ports.notification import NotificationPriority

from todo_app.entrypoints.ch04_event_driven import build_app


@pytest.mark.ch04
def test_admin_deleting_user_todo_emits_notification() -> None:
    """Verify that an admin deleting another user's task dispatches an alert notification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "events_test.db"
        notifier = InMemoryNotificationAdapter()
        app = build_app(db_url=f"sqlite:///{db_path}", notifier=notifier)
        client = TestClient(app)

        # Alice creates a task
        alice_headers = {"Authorization": "Bearer user:alice"}
        create_resp = client.post(
            "/todos",
            json={"title": "Important Client Proposal", "priority": "high"},
            headers=alice_headers,
        )
        assert create_resp.status_code == 201
        todo_id = create_resp.json()["id"]

        # No notifications yet
        assert len(notifier.notifications) == 0

        # Admin deletes Alice's task
        admin_headers = {"Authorization": "Bearer admin:superadmin"}
        del_resp = client.delete(f"/todos/{todo_id}", headers=admin_headers)
        assert del_resp.status_code == 200

        # Verify notification was dispatched via NotificationPort
        assert len(notifier.notifications) == 1
        record = notifier.notifications[0]
        assert "Admin Task Deletion Notice" in record.title
        assert "superadmin" in record.body
        assert "Important Client Proposal" in record.body
        assert "alice" in record.body
        assert record.priority == NotificationPriority.HIGH
        assert "audit" in record.tags


@pytest.mark.ch04
def test_user_deleting_own_todo_does_not_emit_admin_alert() -> None:
    """Verify Alice deleting her own task does not emit an admin deletion alert."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "events_test.db"
        notifier = InMemoryNotificationAdapter()
        app = build_app(db_url=f"sqlite:///{db_path}", notifier=notifier)
        client = TestClient(app)

        # Alice creates a task
        alice_headers = {"Authorization": "Bearer user:alice"}
        create_resp = client.post(
            "/todos",
            json={"title": "My Routine Task", "priority": "low"},
            headers=alice_headers,
        )
        assert create_resp.status_code == 201
        todo_id = create_resp.json()["id"]

        # Alice deletes her own task
        del_resp = client.delete(f"/todos/{todo_id}", headers=alice_headers)
        assert del_resp.status_code == 200

        # No admin alert dispatched
        assert len(notifier.notifications) == 0
