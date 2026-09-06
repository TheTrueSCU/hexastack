"""Unit tests for StdoutNotificationAdapter and InMemoryNotificationAdapter."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from hexastack_core.adapters.notification import (
    InMemoryNotificationAdapter,
    StdoutNotificationAdapter,
)
from hexastack_core.ports.notification import (
    NotificationPort,
    NotificationPriority,
)


def test_in_memory_notification_adapter() -> None:
    """Verify InMemoryNotificationAdapter captures notifications."""
    adapter = InMemoryNotificationAdapter()
    assert isinstance(adapter, NotificationPort)

    res = adapter.notify(
        title="Task Deleted",
        body="Admin deleted Alice's task",
        priority=NotificationPriority.HIGH,
        tags=["audit"],
    )
    assert res is True

    assert len(adapter.notifications) == 1
    record = adapter.notifications[0]
    assert record.title == "Task Deleted"
    assert record.body == "Admin deleted Alice's task"
    assert record.priority == NotificationPriority.HIGH
    assert record.tags == ["audit"]

    # Test default priority and empty tags
    res2 = adapter.notify(
        title="Info Alert",
        body="System check passed",
    )
    assert res2 is True
    assert len(adapter.notifications) == 2
    assert adapter.notifications[1].priority == NotificationPriority.NORMAL
    assert adapter.notifications[1].tags == []

    adapter.clear()
    assert len(adapter.notifications) == 0


def test_stdout_notification_adapter_file_output() -> None:
    """Verify StdoutNotificationAdapter writes alerts to target file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = Path(tmpdir) / "nested" / "dir" / "alerts.log"
        adapter = StdoutNotificationAdapter(output_file=out_file, prefix="[SYSTEM]")

        res = adapter.notify(
            title="500 Internal Error",
            body="Database connection failed",
            priority=NotificationPriority.EMERGENCY,
            tags=["urgent", "db"],
        )
        assert res is True

        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert (
            "[SYSTEM][EMERGENCY] [urgent, db] 500 Internal Error\n  Database connection failed\n"
            in content
        )


def test_stdout_notification_adapter_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify StdoutNotificationAdapter writes alerts to stdout without tags."""
    adapter = StdoutNotificationAdapter()
    res = adapter.notify(
        title="Ready",
        body="Worker online",
        priority=NotificationPriority.LOW,
    )
    assert res is True
    captured = capsys.readouterr()
    assert "🔔 [ALERT][LOW] Ready\n  Worker online\n" in captured.out
