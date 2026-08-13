from hexastack_events.domain.models import OutboxRecord, OutboxStatus
from hexastack_events.ports.outbox import OutboxStoragePort


class InMemoryOutboxStorage(OutboxStoragePort):
    """In-memory thread-safe implementation of OutboxStoragePort for testing and local dev.

    Notes/Architectural Intent:
        Stores staged outbox records in a dictionary, simulating database transactions
        and enabling deterministic test assertions on staged vs published records.
    """

    def __init__(self) -> None:
        self._records: dict[str, OutboxRecord] = {}

    def save(self, record: OutboxRecord) -> None:
        self._records[record.id] = record

    def save_all(self, records: list[OutboxRecord]) -> None:
        for r in records:
            self._records[r.id] = r

    def fetch_pending(self, limit: int = 50) -> list[OutboxRecord]:
        pending = [
            r
            for r in self._records.values()
            if r.status in (OutboxStatus.PENDING, OutboxStatus.FAILED)
            and r.retry_count < 5
        ]
        pending.sort(key=lambda r: r.created_at)
        return pending[:limit]

    def mark_published(self, record_id: str) -> None:
        if record_id in self._records:
            self._records[record_id].mark_published()

    def mark_failed(self, record_id: str, error_message: str) -> None:
        if record_id in self._records:
            self._records[record_id].mark_failed(error_message)

    def get_all(self) -> list[OutboxRecord]:
        """Return all stored outbox records."""
        return list(self._records.values())

    def clear(self) -> None:
        """Clear all stored outbox records."""
        self._records.clear()


__all__ = [
    "InMemoryOutboxStorage",
]
