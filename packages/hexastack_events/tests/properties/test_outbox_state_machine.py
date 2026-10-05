"""Stateful property-based fuzz testing for Outbox relay invariants."""

from datetime import UTC, datetime

from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    rule,
)

from hexastack_events.adapters.outbox.in_memory import InMemoryOutboxStorage
from hexastack_events.domain.models import OutboxRecord, OutboxStatus


class OutboxRelayStateMachine(RuleBasedStateMachine):
    """Hypothesis RuleBasedStateMachine mathematically verifying Outbox relay state transitions.

    Notes/Architectural Intent:
        Exercises arbitrary interleaved transitions:
        - enqueueing events
        - fetching pending batches
        - marking successes and failures
        - retry budget exhaustion
        Proves invariants:
        1. No published event is ever re-fetched as pending.
        2. Events with retry_count >= 5 are never returned in fetch_pending.
        3. Total records in storage equals count of enqueued unique IDs.
    """

    def __init__(self) -> None:
        super().__init__()
        self.storage = InMemoryOutboxStorage()
        self.known_ids: set[str] = set()
        self.published_ids: set[str] = set()
        self.delivered_records: dict[str, int] = {}

    @rule(
        event_id=st.text(
            min_size=1, max_size=30, alphabet=st.characters(categories=["L", "N"])
        ),
        event_type=st.sampled_from(
            ["OrderCreated", "PaymentReceived", "UserRegistered"]
        ),
    )
    def enqueue_event(self, event_id: str, event_type: str) -> None:
        """Enqueue a new outbox record."""
        if event_id not in self.known_ids:
            record = OutboxRecord(
                id=event_id,
                event_type=event_type,
                payload={"id": event_id},
                created_at=datetime.now(UTC),
            )
            self.storage.save(record)
            self.known_ids.add(event_id)

    @rule(limit=st.integers(min_value=1, max_value=20))
    def process_batch(self, limit: int) -> None:
        """Fetch pending batch and simulate dispatch."""
        pending = self.storage.fetch_pending(limit=limit)
        assert len(pending) <= limit

        for record in pending:
            assert record.id in self.known_ids
            assert record.id not in self.published_ids
            assert record.retry_count < 5
            assert record.status in (OutboxStatus.PENDING, OutboxStatus.FAILED)

    @rule(data=st.data())
    def mark_random_published(self, data: st.DataObject) -> None:
        """Mark a pending record as published."""
        pending = self.storage.fetch_pending(limit=100)
        if pending:
            chosen = data.draw(st.sampled_from(pending))
            self.storage.mark_published(chosen.id)
            self.published_ids.add(chosen.id)

    @rule(data=st.data(), error_msg=st.text(min_size=1, max_size=50))
    def mark_random_failed(self, data: st.DataObject, error_msg: str) -> None:
        """Mark a pending record as failed with an error message."""
        pending = self.storage.fetch_pending(limit=100)
        if pending:
            chosen = data.draw(st.sampled_from(pending))
            self.storage.mark_failed(chosen.id, error_msg)

    @rule(data=st.data(), crash_ratio=st.floats(min_value=0.1, max_value=0.9))
    def simulate_worker_crash_during_batch(
        self, data: st.DataObject, crash_ratio: float
    ) -> None:
        """Simulate unexpected worker crash halfway through processing a batch."""
        pending = self.storage.fetch_pending(limit=20)
        if not pending:
            return

        crash_point = max(1, int(len(pending) * crash_ratio))
        published_before_crash = pending[:crash_point]

        # Downstream receives events before crash, but worker dies before mark_published
        for rec in published_before_crash:
            self.delivered_records[rec.id] = self.delivered_records.get(rec.id, 0) + 1

    @rule()
    def recover_from_crash(self) -> None:
        """Simulate a rebooted relay worker draining pending records after crash."""
        pending = self.storage.fetch_pending(limit=20)
        for rec in pending:
            self.delivered_records[rec.id] = self.delivered_records.get(rec.id, 0) + 1
            self.storage.mark_published(rec.id)
            self.published_ids.add(rec.id)

    @invariant()
    def storage_integrity(self) -> None:
        """Verify storage invariant consistency."""
        all_records = self.storage.get_all()
        assert len(all_records) == len(self.known_ids)

        for record in all_records:
            if record.id in self.published_ids:
                assert record.status == OutboxStatus.PUBLISHED
                assert record.published_at is not None
            if record.retry_count >= 5:
                assert record not in self.storage.fetch_pending(limit=100)

    @invariant()
    def deduplication_idempotency_invariant(self) -> None:
        """Verify that every published record corresponds to a unique known id and is terminal."""
        for rec_id in self.published_ids:
            matching = [r for r in self.storage.get_all() if r.id == rec_id]
            assert len(matching) == 1
            assert matching[0].status == OutboxStatus.PUBLISHED
            assert matching[0] not in self.storage.fetch_pending(limit=100)


TestOutboxRelayStateMachine = OutboxRelayStateMachine.TestCase
