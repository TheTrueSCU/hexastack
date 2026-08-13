from abc import ABC, abstractmethod

from hexastack_events.domain.models import OutboxRecord


class OutboxStoragePort(ABC):
    """Abstract port for persisting and updating OutboxRecords.

    Notes/Architectural Intent:
        Implemented by database adapters (SQLAlchemy in hexastack-db, SQLite,
        or InMemory for testing) to store records within transaction boundaries.
    """

    @abstractmethod
    def save(self, record: OutboxRecord) -> None:
        """Persist a new outbox record.

        Args:
            record: OutboxRecord instance.
        """

    @abstractmethod
    def save_all(self, records: list[OutboxRecord]) -> None:
        """Persist multiple outbox records in a batch.

        Args:
            records: List of OutboxRecord instances.
        """

    @abstractmethod
    def fetch_pending(self, limit: int = 50) -> list[OutboxRecord]:
        """Fetch pending outbox records ready for relaying.

        Args:
            limit: Maximum number of records to retrieve.

        Returns:
            List of pending OutboxRecord instances ordered by creation time.
        """

    @abstractmethod
    def mark_published(self, record_id: str) -> None:
        """Mark an outbox record as successfully delivered.

        Args:
            record_id: Unique record ID.
        """

    @abstractmethod
    def mark_failed(self, record_id: str, error_message: str) -> None:
        """Mark an outbox record as failed with an error message.

        Args:
            record_id: Unique record ID.
            error_message: Failure diagnostics.
        """


class OutboxRelayPort(ABC):
    """Abstract port for background workers draining and publishing outbox events.

    Notes/Architectural Intent:
        Defines the lifecycle and execution contract for outbox pollers/streamers
        (AsyncioOutboxRelay, HueyOutboxRelay).
    """

    @abstractmethod
    def publish_pending_batch(self, limit: int = 50) -> int:
        """Poll and publish a batch of pending outbox records.

        Args:
            limit: Maximum records to drain in this cycle.

        Returns:
            Number of successfully published records.
        """

    @abstractmethod
    def start(self) -> None:
        """Start the background outbox polling loop."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the background outbox polling loop."""


__all__ = [
    "OutboxRelayPort",
    "OutboxStoragePort",
]
