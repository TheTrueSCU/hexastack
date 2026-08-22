"""Unit tests for StdoutNotificationAdapter and InMemoryNotificationAdapter."""

from __future__ import annotations

import tempfile
from pathlib import Path

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

    assert adapter.notify(
        title="Task Deleted",
        body="Admin deleted Alice's task",
        priority=NotificationPriority.HIGH,
        tags=["audit"],
    )

    assert len(adapter.notifications) == 1
    record = adapter.notifications[0]
    assert record.title == "Task Deleted"
    assert record.body == "Admin deleted Alice's task"
    assert record.priority == NotificationPriority.HIGH
    assert record.tags == ["audit"]

    adapter.clear()
    assert len(adapter.notifications) == 0


def test_stdout_notification_adapter_file_output() -> None:
    """Verify StdoutNotificationAdapter writes alerts to target file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = Path(tmpdir) / "alerts.log"
        adapter = StdoutNotificationAdapter(output_file=out_file)

        adapter.notify(
            title="500 Internal Error",
            body="Database connection failed",
            priority=NotificationPriority.EMERGENCY,
            tags=["urgent"],
        )

        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "🔔 [ALERT][EMERGENCY] [urgent] 500 Internal Error" in content
        assert "Database connection failed" in content
