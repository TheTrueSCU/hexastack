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


def test_apprise_adapter_notify_with_ad_hoc_targets() -> None:
    """Verify notify method uses ephemeral dispatcher when targets are specified."""
    mock_mod, mock_instance = _setup_mock_apprise()
    mock_instance.notify.return_value = True

    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "apprise", mock_mod)
        adapter = AppriseNotificationAdapter(urls=["ntfy://base-channel"])
        mock_instance.reset_mock()

        result = adapter.notify(
            title="Job Succeeded",
            body="Job completed in 1.2s",
            priority=NotificationPriority.NORMAL,
            tags=["job"],
            targets=["slack://custom-target", "discord://custom-target"],
        )

        assert result is True
        # Verify ephemeral instance received add calls for both targets
        assert mock_instance.add.call_count == 2
        added_urls = [call[0][0] for call in mock_instance.add.call_args_list]
        assert "slack://custom-target" in added_urls
        assert "discord://custom-target" in added_urls
        mock_instance.notify.assert_called_once()
