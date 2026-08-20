"""Unit tests for AppriseNotificationAdapter and NotificationPort."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

import pytest

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_core.ports.notification import (
    NotificationPort,
    NotificationPriority,
)
from hexastack_events.adapters.notifications.apprise import (
    AppriseNotificationAdapter,
)


def _setup_mock_apprise() -> tuple[Any, MagicMock]:
    """Helper to mock apprise module in sys.modules."""
    mock_apprise_mod: Any = ModuleType("apprise")
    mock_apprise_cls = MagicMock()
    mock_apprise_instance = MagicMock()
    mock_apprise_cls.return_value = mock_apprise_instance

    # Mock NotifyType and NotifyFormat
    mock_apprise_mod.Apprise = mock_apprise_cls
    mock_notify_type = MagicMock()
    mock_notify_type.INFO = "info"
    mock_notify_type.SUCCESS = "success"
    mock_notify_type.WARNING = "warning"
    mock_notify_type.FAILURE = "failure"
    mock_apprise_mod.NotifyType = mock_notify_type

    mock_notify_format = MagicMock()
    mock_notify_format.MARKDOWN = "markdown"
    mock_apprise_mod.NotifyFormat = mock_notify_format

    return mock_apprise_mod, mock_apprise_instance


def test_apprise_adapter_implements_notification_port() -> None:
    """Verify AppriseNotificationAdapter adheres to NotificationPort ABC contract."""
    mock_mod, mock_instance = _setup_mock_apprise()

    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "apprise", mock_mod)
        adapter = AppriseNotificationAdapter(urls=["ntfy://test-topic"])
        assert isinstance(adapter, NotificationPort)
        mock_instance.add.assert_called_once_with("ntfy://test-topic")


def test_apprise_adapter_notify_dispatch() -> None:
    """Verify notify method translates priorities and dispatches through Apprise."""
    mock_mod, mock_instance = _setup_mock_apprise()
    mock_instance.notify.return_value = True

    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "apprise", mock_mod)
        adapter = AppriseNotificationAdapter(
            urls=["discord://webhook_id/webhook_token"]
        )
        result = adapter.notify(
            title="500 Internal Server Error",
            body="**Error**: Database lock timeout",
            priority=NotificationPriority.EMERGENCY,
            tags=["incident", "backend"],
        )

        assert result is True
        mock_instance.notify.assert_called_once()
        _, kwargs = mock_instance.notify.call_args
        assert kwargs["title"] == "500 Internal Server Error"
        assert kwargs["body"] == "**Error**: Database lock timeout"
        assert kwargs["tag"] == ["incident", "backend"]


def test_apprise_adapter_missing_dependency_guard() -> None:
    """Verify MissingDependencyError is raised when apprise import fails."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "apprise", None)
        with pytest.raises(MissingDependencyError) as exc_info:
            AppriseNotificationAdapter()
        assert "Apprise is required" in str(exc_info.value)
