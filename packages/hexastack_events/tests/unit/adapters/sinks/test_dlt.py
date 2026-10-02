"""Unit tests for dlt analytical event lake sink and CQRS projection consumers."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from hexastack_events.adapters.sinks.dlt import (
    DltEventSink,
    DltProjectionConsumer,
    _normalize_event,
    _require_dlt,
    dlt_event_source,
    dlt_outbox_source,
)
from hexastack_events.domain.exceptions import EventDeliveryError
from hexastack_events.domain.models import (
    CloudEventEnvelope,
    OutboxRecord,
    OutboxStatus,
)


class SamplePydanticEvent(BaseModel):
    """Sample Pydantic domain event for testing."""

    order_id: str
    amount: float


@dataclasses.dataclass
class SampleDataclassEvent:
    """Sample dataclass domain event for testing."""

    user_id: str
    action: str


class SampleGenericEvent:
    """Sample plain class domain event."""

    def __init__(self, key: str, value: int) -> None:
        self.key = key
        self.value = value


class UnserializableObject:
    """Object without __dict__ (slots only) that fails normalization."""

    __slots__ = ()


def _duckdb_dest(tmp_path: Path, name: str = "test.duckdb") -> Any:
    """Helper to create an isolated duckdb destination in tmp_path."""
    dlt_mod = _require_dlt()
    return dlt_mod.destinations.duckdb(str(tmp_path / name))


def test_require_dlt_success() -> None:
    """Test _require_dlt returns the dlt module when installed."""
    mod = _require_dlt()
    assert mod is not None
    assert hasattr(mod, "pipeline")


def test_require_dlt_missing_import() -> None:
    """Test _require_dlt raises an informative ImportError when dlt is absent."""
    with (
        patch(
            "importlib.import_module", side_effect=ImportError("No module named 'dlt'")
        ),
        pytest.raises(ImportError, match=r"pip install hexastack-events\[dlt\]"),
    ):
        _require_dlt()


def test_normalize_event_cloudevent_envelope() -> None:
    """Test normalization of CloudEventEnvelope instances."""
    envelope = CloudEventEnvelope(
        id="evt-100",
        type="order.created",
        source="order-service",
        time="2026-09-07T12:00:00Z",
        datacontenttype="application/json",
        correlationid="corr-1",
        tenantid="tenant-alpha",
        data={"order_id": "ord-1", "total": 42.5},
    )
    row = _normalize_event(envelope)
    assert row["event_id"] == "evt-100"
    assert row["event_type"] == "order.created"
    assert row["source"] == "order-service"
    assert row["time"] == "2026-09-07T12:00:00Z"
    assert row["correlation_id"] == "corr-1"
    assert row["tenant_id"] == "tenant-alpha"
    assert row["data"] == {"order_id": "ord-1", "total": 42.5}


def test_normalize_event_outbox_record() -> None:
    """Test normalization of OutboxRecord instances with and without published_at."""
    now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=UTC)
    rec1 = OutboxRecord(
        id="rec-1",
        event_type="user.registered",
        source="auth-service",
        payload={"username": "alice"},
        status=OutboxStatus.PUBLISHED,
        retry_count=0,
        correlation_id="c-1",
        tenant_id="t-1",
        created_at=now,
        published_at=now,
        last_error=None,
    )
    row1 = _normalize_event(rec1)
    assert row1["record_id"] == "rec-1"
    assert row1["event_type"] == "user.registered"
    assert row1["status"] == "PUBLISHED"
    assert row1["created_at"] == now.isoformat()
    assert row1["published_at"] == now.isoformat()

    rec2 = OutboxRecord(
        id="rec-2",
        event_type="user.registered",
        source="auth-service",
        payload={"username": "bob"},
        status=OutboxStatus.PENDING,
        created_at=now,
    )
    row2 = _normalize_event(rec2)
    assert row2["record_id"] == "rec-2"
    assert row2["published_at"] is None


def test_normalize_event_pydantic() -> None:
    """Test normalization of Pydantic models."""
    evt = SamplePydanticEvent(order_id="ord-99", amount=199.99)
    row = _normalize_event(evt)
    assert row["order_id"] == "ord-99"
    assert row["amount"] == 199.99
    assert row["event_type"] == "SamplePydanticEvent"


def test_normalize_event_dataclass() -> None:
    """Test normalization of dataclasses."""
    evt = SampleDataclassEvent(user_id="usr-12", action="login")
    row = _normalize_event(evt)
    assert row["user_id"] == "usr-12"
    assert row["action"] == "login"
    assert row["event_type"] == "SampleDataclassEvent"


def test_normalize_event_dict_and_generic_class() -> None:
    """Test normalization of plain dictionaries and generic objects."""
    raw_dict = {"event_type": "custom.event", "value": 123}
    assert _normalize_event(raw_dict) == raw_dict

    obj = SampleGenericEvent("k1", 456)
    row_obj = _normalize_event(obj)
    assert row_obj["key"] == "k1"
    assert row_obj["value"] == 456
    assert row_obj["event_type"] == "SampleGenericEvent"


def test_normalize_event_unsupported_type() -> None:
    """Test that unsupported types raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported event type"):
        _normalize_event(UnserializableObject())


def test_dlt_event_sink_initialization(tmp_path: Path) -> None:
    """Test DltEventSink initialization with various configuration options."""
    sink = DltEventSink(
        pipeline_name="test_pipeline_init",
        destination=_duckdb_dest(tmp_path),
        dataset_name="test_lake",
        pipelines_dir=tmp_path / "dlt_state",
        import_schema_path=tmp_path / "import_schema.yml",
        export_schema_path=tmp_path / "export_schema.yml",
        dev_mode=True,
    )
    assert sink.pipeline is not None
    assert sink.pipeline.pipeline_name == "test_pipeline_init"
    assert sink.pipeline.dataset_name.startswith("test_lake")


def test_dlt_event_sink_ingest_empty(tmp_path: Path) -> None:
    """Test that ingesting an empty batch returns None without executing."""
    sink = DltEventSink(
        pipeline_name="empty_test",
        destination=_duckdb_dest(tmp_path),
        pipelines_dir=tmp_path,
    )
    res = sink.ingest([])
    assert res is None


def test_dlt_event_sink_ingest_events_and_duckdb(tmp_path: Path) -> None:
    """Test end-to-end ingestion of CloudEvents and domain events into DuckDB."""
    sink = DltEventSink(
        pipeline_name="events_ingest_test",
        destination=_duckdb_dest(tmp_path),
        dataset_name="analytics",
        pipelines_dir=tmp_path,
    )
    events = [
        CloudEventEnvelope(
            id="evt-1",
            type="order.placed",
            source="checkout",
            time="2026-09-07T12:00:00Z",
            data={"order_id": "o-1", "price": 10.0},
        ),
        SamplePydanticEvent(order_id="o-2", amount=20.0),
        {"event_type": "metric.recorded", "metric": "cpu", "value": 45.2},
    ]

    info = sink.ingest(
        events,
        table_name="events_table",
        write_disposition="append",
    )
    assert info is not None
    assert not info.has_failed_jobs


def test_dlt_event_sink_ingest_error_handling(tmp_path: Path) -> None:
    """Test that pipeline execution errors are wrapped in EventDeliveryError."""
    sink = DltEventSink(
        pipeline_name="err_test",
        destination=_duckdb_dest(tmp_path),
        pipelines_dir=tmp_path,
    )
    with (
        patch.object(
            sink.pipeline, "run", side_effect=RuntimeError("Storage disk full")
        ),
        pytest.raises(EventDeliveryError, match="dlt event ingestion failed"),
    ):
        sink.ingest([{"event_type": "test", "data": 1}])


def test_dlt_event_sink_ingest_outbox(tmp_path: Path) -> None:
    """Test ingestion of OutboxRecord instances into DuckDB destination."""
    sink = DltEventSink(
        pipeline_name="outbox_ingest_test",
        destination=_duckdb_dest(tmp_path),
        dataset_name="outbox_lake",
        pipelines_dir=tmp_path,
    )
    assert sink.ingest_outbox([]) is None

    now = datetime(2026, 9, 7, 12, 0, 0, tzinfo=UTC)
    records = [
        OutboxRecord(
            id="outbox-1",
            event_type="item.shipped",
            source="warehouse",
            payload={"tracking": "TRK-123"},
            status=OutboxStatus.PUBLISHED,
            created_at=now,
        ),
    ]

    info = sink.ingest_outbox(records, table_name="outbox_events")
    assert info is not None
    assert not info.has_failed_jobs

    with (
        patch.object(sink.pipeline, "run", side_effect=RuntimeError("Outbox error")),
        pytest.raises(EventDeliveryError, match="dlt outbox ingestion failed"),
    ):
        sink.ingest_outbox(records)


@pytest.mark.asyncio
async def test_dlt_event_sink_async_methods(tmp_path: Path) -> None:
    """Test async ingestion methods offload work to threadpool."""
    sink = DltEventSink(
        pipeline_name="async_test",
        destination=_duckdb_dest(tmp_path),
        pipelines_dir=tmp_path,
    )
    events = [{"event_type": "async.event", "val": 1}]
    info1 = await sink.ingest_async(events, table_name="async_events")
    assert info1 is not None

    record = OutboxRecord(
        id="async-rec-1",
        event_type="async.outbox",
        source="src",
        payload={},
        status=OutboxStatus.PENDING,
    )
    info2 = await sink.ingest_outbox_async([record], table_name="async_outbox")
    assert info2 is not None


def test_dlt_projection_consumer_buffering_and_flush(tmp_path: Path) -> None:
    """Test DltProjectionConsumer buffering threshold auto-flush and manual flush."""
    sink = DltEventSink(
        pipeline_name="consumer_test",
        destination=_duckdb_dest(tmp_path),
        pipelines_dir=tmp_path,
    )
    consumer = DltProjectionConsumer(
        sink=sink,
        batch_size=3,
        table_name="projection_table",
    )

    assert consumer.buffer_size == 0
    assert consumer.flush() is None

    res1 = consumer.consume({"event_type": "event.1", "val": 1})
    assert res1 is None
    assert consumer.buffer_size == 1

    res2 = consumer.consume({"event_type": "event.2", "val": 2})
    assert res2 is None
    assert consumer.buffer_size == 2

    # Third item hits batch_size=3, triggering automatic flush
    res3 = consumer.consume({"event_type": "event.3", "val": 3})
    assert res3 is not None
    assert not res3.has_failed_jobs
    assert consumer.buffer_size == 0

    # Manual flush after partial buffering
    consumer.consume({"event_type": "event.4", "val": 4})
    assert consumer.buffer_size == 1
    flush_res = consumer.flush()
    assert flush_res is not None
    assert consumer.buffer_size == 0


@pytest.mark.asyncio
async def test_dlt_projection_consumer_async(tmp_path: Path) -> None:
    """Test async consume and flush methods on DltProjectionConsumer."""
    sink = DltEventSink(
        pipeline_name="async_consumer_test",
        destination=_duckdb_dest(tmp_path),
        pipelines_dir=tmp_path,
    )
    consumer = DltProjectionConsumer(
        sink=sink,
        batch_size=2,
        table_name="async_proj",
    )

    res1 = await consumer.consume_async({"event_type": "e1"})
    assert res1 is None
    assert consumer.buffer_size == 1

    res2 = await consumer.flush_async()
    assert res2 is not None
    assert consumer.buffer_size == 0


def test_dlt_sources_and_pipeline_execution(tmp_path: Path) -> None:
    """Test dlt_event_source and dlt_outbox_source standalone sources."""
    dlt_mod = _require_dlt()
    events = [
        CloudEventEnvelope(
            id="src-evt-1",
            type="payment.processed",
            source="billing",
            time="2026-09-07T12:00:00Z",
            data={"amount": 49.99},
        ),
    ]
    source = dlt_event_source(events, table_name="src_events")
    p1 = dlt_mod.pipeline(
        pipeline_name="src_pipeline_events",
        destination=_duckdb_dest(tmp_path, "p1.duckdb"),
        pipelines_dir=str(tmp_path),
    )
    info1 = p1.run(source)
    assert not info1.has_failed_jobs

    records = [
        OutboxRecord(
            id="src-rec-1",
            event_type="payment.recorded",
            source="billing",
            payload={"receipt": "R-100"},
            status=OutboxStatus.PUBLISHED,
        ),
    ]
    outbox_src = dlt_outbox_source(records, table_name="src_outbox")
    p2 = dlt_mod.pipeline(
        pipeline_name="src_pipeline_outbox",
        destination=_duckdb_dest(tmp_path, "p2.duckdb"),
        pipelines_dir=str(tmp_path),
    )
    info2 = p2.run(outbox_src)
    assert not info2.has_failed_jobs
