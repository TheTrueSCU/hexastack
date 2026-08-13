from datetime import UTC, datetime

import pytest
from hexastack_events.adapters.outbox.sqlalchemy import (
    Base,
    OutboxEventBaseModel,
    SqlAlchemyOutboxStorage,
)
from hexastack_events.domain.models import OutboxRecord, OutboxStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_session():
    """Fixture providing a clean in-memory SQLite database session."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_sqlalchemy_outbox_storage_save_and_fetch(db_session):
    storage = SqlAlchemyOutboxStorage(session_factory=db_session)

    record = OutboxRecord(
        id="rec-sql-1",
        event_type="OrderPaidEvent",
        source="billing-service",
        payload={"order_id": "ord-1", "total": 99.50},
        correlation_id="corr-sql-10",
        tenant_id="tenant-acme",
        created_at=datetime.now(UTC),
    )

    storage.save(record)

    pending = storage.fetch_pending(limit=10)
    assert len(pending) == 1
    assert pending[0].id == "rec-sql-1"
    assert pending[0].event_type == "OrderPaidEvent"
    assert pending[0].payload["total"] == 99.50
    assert pending[0].correlation_id == "corr-sql-10"
    assert pending[0].tenant_id == "tenant-acme"
    assert pending[0].status == OutboxStatus.PENDING


def test_sqlalchemy_outbox_storage_lifecycle(db_session):
    storage = SqlAlchemyOutboxStorage(session_factory=db_session)

    rec1 = OutboxRecord(
        id="rec-sql-a",
        event_type="ItemCreated",
        source="catalog",
        payload={"item_id": "i1"},
    )
    rec2 = OutboxRecord(
        id="rec-sql-b",
        event_type="ItemUpdated",
        source="catalog",
        payload={"item_id": "i2"},
    )

    storage.save_all([rec1, rec2])

    pending = storage.fetch_pending(limit=10)
    assert len(pending) == 2

    # Mark rec1 as published
    storage.mark_published("rec-sql-a")
    pending_after = storage.fetch_pending(limit=10)
    assert len(pending_after) == 1
    assert pending_after[0].id == "rec-sql-b"

    # Mark rec2 as failed
    storage.mark_failed("rec-sql-b", "Kafka unreachable")
    row_b = db_session.get(OutboxEventBaseModel, "rec-sql-b")
    assert row_b.status == OutboxStatus.FAILED.value
    assert row_b.retry_count == 1
    assert row_b.last_error == "Kafka unreachable"
