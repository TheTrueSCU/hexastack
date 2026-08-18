from collections import defaultdict
from collections.abc import Callable
from typing import Any

from hexastack_core.domain import Event
from hexastack_events.domain.models import CloudEventEnvelope
from hexastack_events.ports.buses import DistributedEventBusPort


class InMemoryDistributedEventBus(DistributedEventBusPort):
    """In-memory implementation of DistributedEventBusPort for testing and local dev.

    Notes/Architectural Intent:
        Records published CloudEvents envelopes, maintains topic subscriptions,
        and allows verifying published events without external message brokers.
    """

    def __init__(self) -> None:
        self.published_events: list[Event] = []
        self.published_envelopes: list[CloudEventEnvelope] = []
        self._subscribers: dict[str, list[Callable[[Any], Any]]] = defaultdict(list)

    def clear(self) -> None:
        """Clear recorded events and envelopes."""
        self.published_events.clear()
        self.published_envelopes.clear()

    def publish(self, event: Event) -> None:
        """Publish a domain event and invoke local subscribers."""
        self.published_events.append(event)
        event_name = event.__class__.__name__
        for handler in self._subscribers.get(event_name, []):
            handler(event)

    def publish_envelope(self, envelope: CloudEventEnvelope) -> None:
        """Publish a CloudEvents envelope and invoke matching subscribers."""
        self.published_envelopes.append(envelope)
        for handler in self._subscribers.get(envelope.type, []):
            handler(envelope)

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[Any], Any],
    ) -> None:
        """Register a subscriber callback for a specific event type."""
        self._subscribers[event_type].append(handler)


__all__ = [
    "InMemoryDistributedEventBus",
]
