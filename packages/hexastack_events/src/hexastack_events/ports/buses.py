from abc import abstractmethod
from collections.abc import Callable
from typing import Any

from hexastack_core.domain import Event
from hexastack_cqrs.ports.buses import EventBusPort
from hexastack_events.domain.models import CloudEventEnvelope


class DistributedEventBusPort(EventBusPort):
    """Abstract port for cross-service, broker-backed distributed event buses.

    Notes/Architectural Intent:
        Extends EventBusPort to support CloudEvents envelope dispatch and topic-based
        multi-service subscriptions across message brokers (Redis, NATS, Kafka).
    """

    @abstractmethod
    def publish_envelope(self, envelope: CloudEventEnvelope) -> None:
        """Publish a pre-formatted CloudEvents envelope directly to the broker.

        Args:
            envelope: Standard CloudEventEnvelope instance.
        """

    @abstractmethod
    def subscribe(
        self,
        event_type: str,
        handler: Callable[[Event], Any],
    ) -> None:
        """Subscribe a handler callback to a specific distributed event type.

        Args:
            event_type: String identifier of target event type.
            handler: Callable invoked when matching events arrive.
        """


__all__ = [
    "DistributedEventBusPort",
]
