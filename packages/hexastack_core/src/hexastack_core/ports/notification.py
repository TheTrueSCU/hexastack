"""Notification and alert dispatching port interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum


class NotificationPriority(Enum):
    """Notification urgency level mapped to transport delivery mechanisms.

    Notes/Architectural Intent:
        Represents semantic urgency of an alert, allowing adapters (like Apprise,
        ntfy, Slack, PagerDuty) to route to appropriate priority headers or channels.
    """

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EMERGENCY = "emergency"


class NotificationPort(ABC):
    """Abstract secondary port for dispatching operational alerts and push notifications.

    Notes/Architectural Intent:
        Abstracts multi-target notification delivery (Apprise, ntfy, Webhooks, Push, SMS, ChatOps)
        away from domain and application kernels. Implementations may broadcast to one or more
        destinations synchronously or asynchronously.
    """

    @abstractmethod
    def notify(
        self,
        title: str,
        body: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        tags: list[str] | None = None,
    ) -> bool:
        """Send a notification message to configured destinations.

        Args:
            title: Subject, summary, or headline of the notification.
            body: Markdown or plaintext content describing the event, digest, or alert.
            priority: Semantic urgency level of the notification.
            tags: Optional tags/categories used by providers (e.g. ntfy tags, slack channels, emojis).

        Returns:
            True if notification dispatched successfully to at least one target, False otherwise.

        Raises:
            Exception: Implementations should log delivery failures but propagate critical transport errors if unhandled.
        """
        ...


__all__ = [
    "NotificationPort",
    "NotificationPriority",
]
