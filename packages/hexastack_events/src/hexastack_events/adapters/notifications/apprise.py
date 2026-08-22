"""Apprise multi-channel notification and alerting adapter."""

from __future__ import annotations

import importlib
from typing import Any

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_core.ports.notification import (
    NotificationPort,
    NotificationPriority,
)


def _get_apprise_module() -> Any:
    """Import and return the apprise module or raise MissingDependencyError."""
    try:
        return importlib.import_module("apprise")
    except (ImportError, ModuleNotFoundError) as e:
        raise MissingDependencyError(
            "Apprise is required for AppriseNotificationAdapter. "
            "Install with 'pip install hexastack-events[apprise]' or 'pip install apprise'."
        ) from e


def _map_priority_to_apprise(priority: NotificationPriority, apprise_mod: Any) -> Any:
    """Map Hexastack NotificationPriority to Apprise NotifyType."""
    priority_map = {
        NotificationPriority.LOW: apprise_mod.NotifyType.INFO,
        NotificationPriority.NORMAL: apprise_mod.NotifyType.SUCCESS,
        NotificationPriority.HIGH: apprise_mod.NotifyType.WARNING,
        NotificationPriority.EMERGENCY: apprise_mod.NotifyType.FAILURE,
    }
    return priority_map.get(priority, apprise_mod.NotifyType.INFO)


class AppriseNotificationAdapter(NotificationPort):
    """Universal notification and alerting adapter powered by Apprise.

    Notes/Architectural Intent:
        Broadcasts alerts, digests, and operational notifications to 80+ messaging services
        (ntfy.sh, Healthchecks.io, Discord, Slack, Telegram, PagerDuty, Webhooks, Email)
        via uniform URI schemas.
    """

    def __init__(
        self,
        urls: str | list[str] | None = None,
        asset: Any | None = None,
    ) -> None:
        """Initialize Apprise notification adapter with target URLs.

        Args:
            urls: Single URL string or list of Apprise service URL strings (e.g. ['ntfy://mytopic']).
            asset: Optional Apprise AppriseAsset configuration.

        Raises:
            MissingDependencyError: If `apprise` library is not installed.
        """
        apprise_mod = _get_apprise_module()
        self._apprise: Any = apprise_mod.Apprise(asset=asset)
        if urls:
            if isinstance(urls, str):
                urls = [urls]
            for url in urls:
                self._apprise.add(url)

    def add_url(self, url: str) -> None:
        """Add an additional notification destination URL to the broadcaster.

        Args:
            url: Target service URL.
        """
        self._apprise.add(url)

    def notify(
        self,
        title: str,
        body: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        tags: list[str] | None = None,
    ) -> bool:
        """Send notification to all configured Apprise targets.

        Args:
            title: Headline or summary of the alert.
            body: Detailed message content.
            priority: Urgency level of the alert.
            tags: Optional tags/categories passed to matching providers.

        Returns:
            True if delivered successfully to at least one target (or no targets configured), False otherwise.
        """
        apprise_mod = _get_apprise_module()
        notify_type = _map_priority_to_apprise(priority, apprise_mod)
        body_format = apprise_mod.NotifyFormat.MARKDOWN

        return bool(
            self._apprise.notify(
                title=title,
                body=body,
                notify_type=notify_type,
                body_format=body_format,
                tag=tags,
            )
        )


__all__ = [
    "AppriseNotificationAdapter",
]
