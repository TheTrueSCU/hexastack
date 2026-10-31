"""Unit tests for notification ports."""

import inspect

import pytest

from hexastack_core.ports.notification import NotificationPort, NotificationPriority


def test_notification_priority_levels() -> None:
    assert NotificationPriority.LOW.value == "low"
    assert NotificationPriority.EMERGENCY.value == "emergency"


def test_notification_port_is_abstract() -> None:
    """Verify that NotificationPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(NotificationPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        NotificationPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_notification_port_abstract_methods() -> None:
    """Verify abstract methods on NotificationPort."""
    expected = {"notify"}
    abstracts = NotificationPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
