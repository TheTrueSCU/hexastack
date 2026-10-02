"""Hypothesis RuleBasedStateMachine dual-implementation oracle tests for Outbox storage.

Notes/Architectural Intent:
    Validates that SqlAlchemyOutboxStorage (relational SQLite persistence adapter) and
    InMemoryOutboxStorage (in-memory reference adapter) maintain exact state and
    behavioral parity across arbitrary sequences of event staging, batch fetching,
    status transitions, retry count increments, and retry budget exhaustion.
"""

from datetime import UTC, datetime, timedelta

from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    rule,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from hexastack_events.adapters.outbox.in_memory import InMemoryOutboxStorage
from hexastack_events.adapters.outbox.sqlalchemy import (
    Base,
    OutboxEventBaseModel,
    SqlAlchemyOutboxStorage,
)
from hexastack_events.domain.models import OutboxRecord, OutboxStatus

EVENT_ID_STRATEGY = st.sampled_from(
    [
        "evt_01",
        "evt_02",
        "evt_03",
        "evt_04",
        "evt_05",
        "evt_06",
        "evt_07",
        "evt_08",
        "evt_09",
        "evt_10",
    ]
)
EVENT_TYPE_STRATEGY = st.sampled_from(
    [
        "OrderPlaced",
        "PaymentCaptured",
        "InvoiceGenerated",
        "UserRegistered",
    ]
)


class OutboxOracleStateMachine(RuleBasedStateMachine):
    """Hypothesis state machine verifying dual-implementation Outbox storage parity.

    Notes/Architectural Intent:
        Executes arbitrary interleaved outbox operations:
        - Staging single events
        - Staging batches of events
        - Fetching pending batches with varying limits
        - Marking individual events as PUBLISHED
        - Marking individual events as FAILED (incrementing retries)
        - Verifying that records reaching 5 retries are evicted from pending queues on both
    """

    def __init__(self) -> None:
        """Initialize state machine, in-memory SQLite schema, and dual outbox adapters."""
        super().__init__()
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.session: Session = self.session_factory()

        self.sql_outbox = SqlAlchemyOutboxStorage(
            session_factory=self.session,
            model_cls=OutboxEventBaseModel,
        )
        self.oracle_outbox = InMemoryOutboxStorage()
        self.known_ids: set[str] = set()
        self.base_time = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
        self.time_offset = 0

    def teardown(self) -> None:
        """Cleanly close database session and dispose SQLite engine."""
        self.session.close()
        self.engine.dispose()

    @rule(event_id=EVENT_ID_STRATEGY, event_type=EVENT_TYPE_STRATEGY)
    def stage_event(self, event_id: str, event_type: str) -> None:
        """Stage a single outbox record across both adapters.

        Args:
            event_id: Unique event identifier.
            event_type: Domain event schema classification.
        """
        if event_id in self.known_ids:
            return

        self.time_offset += 1
        created_at = self.base_time + timedelta(seconds=self.time_offset)
        record = OutboxRecord(
            id=event_id,
            event_type=event_type,
            source="test-service",
            payload={"event_id": event_id, "type": event_type},
            created_at=created_at,
        )

        self.sql_outbox.save(record)
        self.session.commit()
        self.oracle_outbox.save(record.model_copy(deep=True))
        self.known_ids.add(event_id)

    @rule(
        batch=st.lists(
            st.tuples(
                st.text(
                    min_size=2,
                    max_size=8,
                    alphabet=st.characters(categories=["L", "N"]),
                ),
                EVENT_TYPE_STRATEGY,
            ),
            min_size=1,
            max_size=4,
        )
    )
    def stage_batch(self, batch: list[tuple[str, str]]) -> None:
        """Stage multiple outbox records in a batch across both adapters.

        Args:
            batch: List of tuples containing ID and event type.
        """
        records_to_add: list[OutboxRecord] = []
        for raw_id, evt_type in batch:
            batch_id = f"batch_{raw_id}"
            if batch_id not in self.known_ids:
                self.time_offset += 1
                created_at = self.base_time + timedelta(seconds=self.time_offset)
                rec = OutboxRecord(
                    id=batch_id,
                    event_type=evt_type,
                    source="batch-service",
                    payload={"id": batch_id},
                    created_at=created_at,
                )
                self.known_ids.add(batch_id)
                records_to_add.append(rec)

        if not records_to_add:
            return

        self.sql_outbox.save_all(records_to_add)
        self.session.commit()
        self.oracle_outbox.save_all([r.model_copy(deep=True) for r in records_to_add])

    @rule(limit=st.integers(min_value=1, max_value=15))
    def fetch_pending_and_compare(self, limit: int) -> None:
        """Fetch pending records with varying limit and assert exact queue parity.

        Args:
            limit: Maximum number of records to retrieve.
        """
        sql_pending = self.sql_outbox.fetch_pending(limit=limit)
        oracle_pending = self.oracle_outbox.fetch_pending(limit=limit)

        sql_len = len(sql_pending)
        oracle_len = len(oracle_pending)
        assert sql_len == oracle_len

        for s_rec, o_rec in zip(sql_pending, oracle_pending, strict=True):
            assert s_rec.id == o_rec.id
            assert s_rec.status == o_rec.status
            assert s_rec.retry_count == o_rec.retry_count
            assert s_rec.payload == o_rec.payload
            assert s_rec.event_type == o_rec.event_type

    @rule(data=st.data())
    def mark_random_published(self, data: st.DataObject) -> None:
        """Mark a pending record as published and verify eviction from pending.

        Args:
            data: Hypothesis data object for selection.
        """
        pending = self.oracle_outbox.fetch_pending(limit=100)
        if not pending:
            return

        chosen = data.draw(st.sampled_from(pending))
        self.sql_outbox.mark_published(chosen.id)
        self.session.commit()
        self.oracle_outbox.mark_published(chosen.id)

    @rule(
        data=st.data(),
        error_msg=st.text(
            min_size=1, max_size=40, alphabet=st.characters(categories=["L"])
        ),
    )
    def mark_random_failed(self, data: st.DataObject, error_msg: str) -> None:
        """Mark a pending record as failed, incrementing retry count across both adapters.

        Args:
            data: Hypothesis data object for selection.
            error_msg: Error description.
        """
        pending = self.oracle_outbox.fetch_pending(limit=100)
        if not pending:
            return

        chosen = data.draw(st.sampled_from(pending))
        self.sql_outbox.mark_failed(chosen.id, error_msg)
        self.session.commit()
        self.oracle_outbox.mark_failed(chosen.id, error_msg)

    @invariant()
    def outbox_queue_equivalence(self) -> None:
        """Invariant: entire pending queue must be identical between SQL and Oracle."""
        sql_pending = self.sql_outbox.fetch_pending(limit=1000)
        oracle_pending = self.oracle_outbox.fetch_pending(limit=1000)

        sql_ids = [r.id for r in sql_pending]
        oracle_ids = [r.id for r in oracle_pending]
        assert sql_ids == oracle_ids

        sql_statuses = [r.status for r in sql_pending]
        oracle_statuses = [r.status for r in oracle_pending]
        assert sql_statuses == oracle_statuses

        sql_retries = [r.retry_count for r in sql_pending]
        oracle_retries = [r.retry_count for r in oracle_pending]
        assert sql_retries == oracle_retries

        for r in sql_pending:
            assert r.retry_count < 5
            assert r.status in (OutboxStatus.PENDING, OutboxStatus.FAILED)


TestOutboxOracle = OutboxOracleStateMachine.TestCase
