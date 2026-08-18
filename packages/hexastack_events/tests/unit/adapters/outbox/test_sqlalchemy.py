from datetime import UTC, datetime

import pytest
from sqlalchemy import DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import sessionmaker

from hexastack_events.adapters.outbox.sqlalchemy import (
    Base,
    OutboxEventBaseModel,
    SqlAlchemyOutboxStorage,
)
from hexastack_events.domain.models import OutboxRecord, OutboxStatus


@pytest.fixture
def db_session_and_factory():
    """Fixture providing a clean in-memory SQLite database session and factory."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session, session_factory
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_outbox_event_columns_and_schema():
    tbl = OutboxEventBaseModel.__table__

    assert isinstance(tbl.c.id.type, String)
    assert tbl.c.id.type.length == 36
    assert tbl.c.id.primary_key is True

    assert isinstance(tbl.c.event_type.type, String)
    assert tbl.c.event_type.type.length == 128
    assert tbl.c.event_type.index is True

    assert isinstance(tbl.c.source.type, String)
    assert tbl.c.source.type.length == 255

    assert isinstance(tbl.c.status.type, String)
    assert tbl.c.status.type.length == 32
    assert tbl.c.status.index is True

    assert isinstance(tbl.c.retry_count.type, Integer)

    assert isinstance(tbl.c.correlation_id.type, String)
    assert tbl.c.correlation_id.type.length == 64
    assert tbl.c.correlation_id.index is True
    assert tbl.c.correlation_id.nullable is True

    assert isinstance(tbl.c.tenant_id.type, String)
    assert tbl.c.tenant_id.type.length == 64
    assert tbl.c.tenant_id.index is True
    assert tbl.c.tenant_id.nullable is True

    assert isinstance(tbl.c.created_at.type, DateTime)
    assert tbl.c.created_at.type.timezone is True
    assert tbl.c.created_at.index is True

    assert isinstance(tbl.c.published_at.type, DateTime)
    assert tbl.c.published_at.type.timezone is True
    assert tbl.c.published_at.nullable is True

    assert isinstance(tbl.c.last_error.type, Text)
    assert tbl.c.last_error.nullable is True


def test_outbox_event_mixin_to_domain():
    now = datetime(2026, 8, 14, 10, 0, 0, tzinfo=UTC)
    row = OutboxEventBaseModel(
        id="mix-1",
        event_type="UserRegistered",
        source="auth",
        payload={"uid": "u1"},
        status="PENDING",
        retry_count=2,
        correlation_id="c-1",
        tenant_id="t-1",
        created_at=now,
        published_at=None,
        last_error="retry error",
    )
    domain_rec = row.to_domain()
    assert domain_rec.id == "mix-1"
    assert domain_rec.event_type == "UserRegistered"
    assert domain_rec.source == "auth"
    assert domain_rec.payload == {"uid": "u1"}
    assert domain_rec.status == OutboxStatus.PENDING
    assert domain_rec.retry_count == 2
    assert domain_rec.correlation_id == "c-1"
    assert domain_rec.tenant_id == "t-1"
    assert domain_rec.created_at == now
    assert domain_rec.last_error == "retry error"


def test_sqlalchemy_outbox_storage_lifecycle_and_ordering(
    db_session_and_factory,
):
    session, _ = db_session_and_factory
    storage = SqlAlchemyOutboxStorage(session_factory=session)

    t1 = datetime(2026, 8, 14, 9, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 8, 14, 9, 5, 0, tzinfo=UTC)

    rec1 = OutboxRecord(
        id="rec-sql-a",
        event_type="ItemCreated",
        source="catalog",
        payload={"item_id": "i1"},
        created_at=t1,
    )
    rec2 = OutboxRecord(
        id="rec-sql-b",
        event_type="ItemUpdated",
        source="catalog",
        payload={"item_id": "i2"},
        created_at=t2,
    )

    storage.save_all([rec1, rec2])

    # Limit check: oldest first
    pending_limit1 = storage.fetch_pending(limit=1)
    assert len(pending_limit1) == 1
    assert pending_limit1[0].id == "rec-sql-a"

    # Mark rec1 as published
    storage.mark_published("rec-sql-a")
    row_a = session.get(OutboxEventBaseModel, "rec-sql-a")
    assert row_a.status == OutboxStatus.PUBLISHED.value
    assert row_a.published_at is not None

    pending_after = storage.fetch_pending(limit=10)
    assert len(pending_after) == 1
    assert pending_after[0].id == "rec-sql-b"

    # Mark rec2 as failed
    storage.mark_failed("rec-sql-b", "Kafka unreachable")
    row_b = session.get(OutboxEventBaseModel, "rec-sql-b")
    assert row_b.status == OutboxStatus.FAILED.value
    assert row_b.retry_count == 1
    assert row_b.last_error == "Kafka unreachable"


def test_sqlalchemy_outbox_storage_save_and_fetch(db_session_and_factory):
    _session, factory = db_session_and_factory
    # Test using callable factory as session_factory
    storage = SqlAlchemyOutboxStorage(session_factory=factory)

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
