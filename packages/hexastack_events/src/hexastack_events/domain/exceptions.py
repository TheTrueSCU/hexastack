from hexastack_core.domain.exceptions import HexastackError


class EventError(HexastackError):
    """Base domain exception for all event streaming and outbox errors.

    Notes/Architectural Intent:
        Extends HexastackError to allow application handlers to catch all
        event subsystem failures uniformly.
    """


class OutboxError(EventError):
    """Exception raised when an outbox persistence or relay operation fails."""


class EventSerializationError(EventError):
    """Exception raised when CloudEvents serialization or deserialization fails."""


class EventDeliveryError(EventError):
    """Exception raised when an event cannot be published to a destination broker."""


class DuplicateEventError(EventError):
    """Exception raised when an idempotent consumer encounters a duplicated event ID."""


__all__ = [
    "DuplicateEventError",
    "EventDeliveryError",
    "EventError",
    "EventSerializationError",
    "OutboxError",
]
