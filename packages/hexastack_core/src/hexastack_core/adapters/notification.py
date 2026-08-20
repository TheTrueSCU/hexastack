"""Standard and in-memory notification and alert adapters implementing NotificationPort."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from hexastack_core.ports.notification import (
    NotificationPort,
    NotificationPriority,
)


@dataclass(frozen=True)
class NotificationRecord:
    """Immutable record of a dispatched notification."""

    title: str
    body: str
    priority: NotificationPriority
    tags: list[str]


class StdoutNotificationAdapter(NotificationPort):
    """Notification adapter printing formatted alerts to stdout or a file/stream.

    Notes/Architectural Intent:
        Zero-dependency, turn-key adapter for local development, tutorials, and container logs.
        Allows users to see instant visual confirmation of events and alerts without external setup.
    """

    def __init__(
        self,
        output_file: Path | str | None = None,
        prefix: str = "🔔 [ALERT]",
    ) -> None:
        """Initialize StdoutNotificationAdapter.

        Args:
            output_file: Optional file path to append notifications to (defaults to stdout).
            prefix: Visual prefix tag for log output.
        """
        self.output_file = Path(output_file) if output_file else None
        self.prefix = prefix

    def notify(
        self,
        title: str,
        body: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        tags: list[str] | None = None,
    ) -> bool:
        """Format and write alert to stdout or destination file."""
        tag_str = f" [{', '.join(tags)}]" if tags else ""
        formatted = (
            f"{self.prefix}[{priority.value.upper()}]{tag_str} {title}\n  {body}\n"
        )

        if self.output_file:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            with self.output_file.open("a", encoding="utf-8") as f:
                f.write(formatted)
        else:
            sys.stdout.write(formatted)
            sys.stdout.flush()

        return True


class InMemoryNotificationAdapter(NotificationPort):
    """In-memory notification adapter capturing dispatched alerts in an accessible list."""

    def __init__(self) -> None:
        """Initialize empty in-memory notification storage."""
        self.notifications: list[NotificationRecord] = []

    def notify(
        self,
        title: str,
        body: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        tags: list[str] | None = None,
    ) -> bool:
        """Record notification in memory."""
        self.notifications.append(
            NotificationRecord(
                title=title,
                body=body,
                priority=priority,
                tags=list(tags or []),
            )
        )
        return True

    def clear(self) -> None:
        """Clear recorded notifications."""
        self.notifications.clear()


__all__ = [
    "InMemoryNotificationAdapter",
    "NotificationRecord",
    "StdoutNotificationAdapter",
]
