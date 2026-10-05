"""Unit tests for notification ports."""

from hexastack_core.ports.notification import NotificationPriority


def test_notification_priority_levels() -> None:
    assert NotificationPriority.LOW.value == "low"
    assert NotificationPriority.EMERGENCY.value == "emergency"
