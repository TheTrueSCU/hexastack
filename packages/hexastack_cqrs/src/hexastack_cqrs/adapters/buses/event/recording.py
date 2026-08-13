from typing import TypeVar

from hexastack_core.domain import Event

from hexastack_cqrs.adapters.buses.event.synchronous import SynchronousEventBus
from hexastack_cqrs.infra.middleware.generic import GenericMiddleware

E = TypeVar("E", bound=Event)


class RecordingEventBus(SynchronousEventBus):
    """In-memory event bus that records all published events for inspection and test assertions.

    Notes/Architectural Intent:
        Extends SynchronousEventBus to capture an in-memory chronological journal of
        published domain events. Enables straightforward test assertions (e.g.
        `bus.assert_published(UserCreatedEvent)`) without requiring custom mock tracking.
    """

    def __init__(self, middleware: list[GenericMiddleware] | None = None) -> None:
        super().__init__(middleware=middleware)
        self.published_events: list[Event] = []

    def publish(self, event: Event) -> None:
        """Publish a domain event, record it to history, and dispatch to handlers."""
        self.published_events.append(event)
        super().publish(event)

    def has_published(self, event_cls: type[Event]) -> bool:
        """Check if any event of the specified class was published."""
        return any(isinstance(e, event_cls) for e in self.published_events)

    def get_published(self, event_cls: type[E]) -> list[E]:
        """Retrieve all recorded published events of a specific type."""
        return [e for e in self.published_events if isinstance(e, event_cls)]

    def assert_published(
        self, event_cls: type[Event], count: int | None = None
    ) -> None:
        """Assert that an event of the given type was published, optionally checking exact count.

        Raises:
            AssertionError: If the event was not published or count does not match.
        """
        matches = self.get_published(event_cls)
        if not matches:
            raise AssertionError(
                f"Expected event of type {event_cls.__name__} to be published, "
                f"but recorded events were: {[type(e).__name__ for e in self.published_events]}"
            )
        if count is not None and len(matches) != count:
            raise AssertionError(
                f"Expected {count} event(s) of type {event_cls.__name__}, "
                f"but found {len(matches)}"
            )

    def clear_recorded(self) -> None:
        """Clear recorded events journal without removing subscriber handlers."""
        self.published_events.clear()

    def clear(self) -> None:
        """Clear all subscribers and recorded events."""
        super().clear()
        self.published_events.clear()


__all__ = [
    "RecordingEventBus",
]
