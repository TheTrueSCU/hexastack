"""dlt (data load tool) lakehouse ingestion and CQRS event projection sink.

Notes/Architectural Intent:
    Provides streaming and micro-batch ingestion of domain events, CloudEvents,
    and transactional outbox records into analytical data stores (DuckDB, Parquet,
    PostgreSQL, BigQuery, Snowflake) with automated schema evolution and write dispositions.
"""

from __future__ import annotations

import asyncio
import dataclasses
import threading
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, cast

from hexastack_core.domain import Event
from hexastack_events.domain.exceptions import EventDeliveryError
from hexastack_events.domain.models import CloudEventEnvelope, OutboxRecord


def _require_dlt() -> Any:
    """Import and return the dlt module or raise an informative ImportError.

    Returns:
        The imported dlt module.

    Raises:
        ImportError: If dlt is not installed in the active environment.
    """
    try:
        import dlt

        return dlt
    except ImportError as exc:
        raise ImportError(
            "dlt is required for DltEventSink. "
            "Install with: pip install hexastack-events[dlt]"
        ) from exc


def _normalize_event(
    event: CloudEventEnvelope | OutboxRecord | Event | dict[str, Any] | Any,
) -> dict[str, Any]:
    """Normalize domain events, envelopes, and dictionaries into row mappings.

    Args:
        event: Domain event, CloudEvent envelope, outbox record, or dictionary.

    Returns:
        Dictionary representation suitable for analytical ingestion.
    """
    if isinstance(event, CloudEventEnvelope):
        return {
            "event_id": event.id,
            "event_type": event.type,
            "source": event.source,
            "time": event.time,
            "datacontenttype": event.datacontenttype,
            "correlation_id": event.correlationid,
            "tenant_id": event.tenantid,
            "data": event.data,
        }
    if isinstance(event, OutboxRecord):
        status_val = (
            event.status.value if hasattr(event.status, "value") else str(event.status)
        )
        return {
            "record_id": event.id,
            "event_type": event.event_type,
            "source": event.source,
            "payload": event.payload,
            "status": status_val,
            "retry_count": event.retry_count,
            "correlation_id": event.correlation_id,
            "tenant_id": event.tenant_id,
            "created_at": event.created_at.isoformat(),
            "published_at": (
                event.published_at.isoformat() if event.published_at else None
            ),
            "last_error": event.last_error,
        }
    if hasattr(event, "model_dump"):
        dumped = cast("dict[str, Any]", cast("Any", event).model_dump())
        if "event_type" not in dumped and hasattr(event, "__class__"):
            dumped["event_type"] = event.__class__.__name__
        return dumped
    if dataclasses.is_dataclass(event) and not isinstance(event, type):
        dumped = dataclasses.asdict(event)
        if "event_type" not in dumped:
            dumped["event_type"] = event.__class__.__name__
        return dumped
    if isinstance(event, dict):
        return event
    if hasattr(event, "__dict__"):
        dumped = dict(event.__dict__)
        if "event_type" not in dumped:
            dumped["event_type"] = event.__class__.__name__
        return dumped
    raise ValueError(f"Unsupported event type '{type(event)}' for ingestion.")


class DltEventSink:
    """Analytical data sink integrating dlt pipelines for domain events and outbox data.

    Notes/Architectural Intent:
        Implements an ingestion sink converting CloudEvents and domain events into
        vectorized analytical tables (e.g. DuckDB, Parquet, Snowflake) with schema
        inference and evolving types.
    """

    def __init__(
        self,
        pipeline_name: str = "hexastack_events",
        destination: str | Any = "duckdb",
        dataset_name: str = "event_lake",
        *,
        dev_mode: bool = False,
        refresh: str | None = None,
        pipelines_dir: str | Path | None = None,
        import_schema_path: str | Path | None = None,
        export_schema_path: str | Path | None = None,
    ) -> None:
        """Initialize DltEventSink with target destination and dataset parameters.

        Args:
            pipeline_name: Identifying pipeline name for state tracking.
            destination: Ingestion target (e.g. 'duckdb', 'parquet', 'postgres', 'bigquery').
            dataset_name: Target analytical dataset / schema namespace.
            dev_mode: Whether to enable dev mode (temporary isolated tables/dataset).
            refresh: Optional refresh mode ('drop_sources', 'drop_resources', 'drop_data').
            pipelines_dir: Optional root directory to store dlt pipeline state.
            import_schema_path: Optional path to pre-existing schema YAML.
            export_schema_path: Optional path to export inferred schema YAML.
        """
        dlt_mod = _require_dlt()
        self._pipeline_name = pipeline_name
        self._destination = destination
        self._dataset_name = dataset_name
        self._dev_mode = dev_mode
        self._refresh = refresh
        self._pipelines_dir = str(pipelines_dir) if pipelines_dir else None
        self._import_schema_path = (
            str(import_schema_path) if import_schema_path else None
        )
        self._export_schema_path = (
            str(export_schema_path) if export_schema_path else None
        )
        self._lock = threading.RLock()

        pipeline_kwargs: dict[str, Any] = {
            "pipeline_name": self._pipeline_name,
            "destination": self._destination,
            "dataset_name": self._dataset_name,
            "dev_mode": self._dev_mode,
        }
        if self._refresh is not None:
            pipeline_kwargs["refresh"] = self._refresh
        if self._pipelines_dir is not None:
            pipeline_kwargs["pipelines_dir"] = self._pipelines_dir
        if self._import_schema_path is not None:
            pipeline_kwargs["import_schema_path"] = self._import_schema_path
        if self._export_schema_path is not None:
            pipeline_kwargs["export_schema_path"] = self._export_schema_path

        self._pipeline = dlt_mod.pipeline(**pipeline_kwargs)

    @property
    def pipeline(self) -> Any:
        """Return the underlying active dlt pipeline instance."""
        return self._pipeline

    def ingest(
        self,
        events: Sequence[CloudEventEnvelope | Event | dict[str, Any]] | Iterable[Any],
        *,
        table_name: str = "domain_events",
        write_disposition: str = "append",
        primary_key: str | Sequence[str] | None = None,
        merge_key: str | Sequence[str] | None = None,
    ) -> Any:
        """Ingest a batch of domain events or envelopes into the lakehouse.

        Args:
            events: Sequence of domain events, CloudEvents, or dictionaries.
            table_name: Analytical destination table name.
            write_disposition: Ingestion strategy ('append', 'replace', 'merge').
            primary_key: Optional primary key for deduplication / merging.
            merge_key: Optional merge key used when write_disposition='merge'.

        Returns:
            dlt.LoadInfo metadata detailing load packages, timings, and tables.

        Raises:
            EventBusError: If ingestion execution fails.
        """
        rows = [_normalize_event(e) for e in events]
        if not rows:
            return None

        with self._lock:
            try:
                run_kwargs: dict[str, Any] = {
                    "table_name": table_name,
                    "write_disposition": write_disposition,
                }
                if primary_key is not None:
                    run_kwargs["primary_key"] = primary_key
                if merge_key is not None:
                    run_kwargs["merge_key"] = merge_key

                return self._pipeline.run(rows, **run_kwargs)
            except Exception as exc:
                raise EventDeliveryError(f"dlt event ingestion failed: {exc}") from exc

    def ingest_outbox(
        self,
        records: Sequence[OutboxRecord],
        *,
        table_name: str = "outbox_records",
        write_disposition: str = "append",
    ) -> Any:
        """Ingest transactional outbox records into analytical storage.

        Args:
            records: Sequence of OutboxRecord instances.
            table_name: Analytical destination table name (default: 'outbox_records').
            write_disposition: Ingestion mode (default: 'append').

        Returns:
            dlt.LoadInfo metadata.

        Raises:
            EventDeliveryError: If outbox ingestion fails.
        """
        rows = [_normalize_event(r) for r in records]
        if not rows:
            return None

        with self._lock:
            try:
                return self._pipeline.run(
                    rows,
                    table_name=table_name,
                    write_disposition=write_disposition,
                    primary_key="record_id",
                )
            except Exception as exc:
                raise EventDeliveryError(f"dlt outbox ingestion failed: {exc}") from exc

    async def ingest_async(
        self,
        events: Sequence[CloudEventEnvelope | Event | dict[str, Any]] | Iterable[Any],
        *,
        table_name: str = "domain_events",
        write_disposition: str = "append",
        primary_key: str | Sequence[str] | None = None,
        merge_key: str | Sequence[str] | None = None,
    ) -> Any:
        """Asynchronously ingest events without blocking the active asyncio event loop."""
        return await asyncio.to_thread(
            self.ingest,
            events,
            table_name=table_name,
            write_disposition=write_disposition,
            primary_key=primary_key,
            merge_key=merge_key,
        )

    async def ingest_outbox_async(
        self,
        records: Sequence[OutboxRecord],
        *,
        table_name: str = "outbox_records",
        write_disposition: str = "append",
    ) -> Any:
        """Asynchronously ingest outbox records on a threadpool."""
        return await asyncio.to_thread(
            self.ingest_outbox,
            records,
            table_name=table_name,
            write_disposition=write_disposition,
        )


class DltProjectionConsumer:
    """Micro-batching projection consumer buffering events for periodic lakehouse delivery.

    Notes/Architectural Intent:
        Buffers real-time CQRS domain events in memory and periodically flushes
        them in batches to dlt to maximize write throughput and minimize small-file
        fragmentation in columnar lakehouses.
    """

    def __init__(
        self,
        sink: DltEventSink,
        *,
        batch_size: int = 100,
        table_name: str = "domain_events",
        write_disposition: str = "append",
    ) -> None:
        """Initialize projection consumer with target sink and buffering thresholds.

        Args:
            sink: DltEventSink instance managing analytical ingestion.
            batch_size: Maximum buffer size before triggering an automatic flush.
            table_name: Destination analytical table name.
            write_disposition: Ingestion mode ('append', 'replace', 'merge').
        """
        self._sink = sink
        self._batch_size = batch_size
        self._table_name = table_name
        self._write_disposition = write_disposition
        self._buffer: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    @property
    def buffer_size(self) -> int:
        """Return the current number of buffered events awaiting flush."""
        with self._lock:
            return len(self._buffer)

    def consume(self, event: CloudEventEnvelope | Event | dict[str, Any]) -> Any:
        """Consume a single event into the buffer, flushing if threshold is reached.

        Args:
            event: Incoming event instance.

        Returns:
            dlt.LoadInfo if a batch flush was triggered, None otherwise.
        """
        row = _normalize_event(event)
        with self._lock:
            self._buffer.append(row)
            if len(self._buffer) >= self._batch_size:
                return self.flush()
        return None

    def flush(self) -> Any:
        """Immediately flush all buffered events to the analytical sink.

        Returns:
            dlt.LoadInfo metadata from the pipeline load, or None if buffer is empty.
        """
        with self._lock:
            if not self._buffer:
                return None
            items = list(self._buffer)
            self._buffer.clear()

        return self._sink.ingest(
            items,
            table_name=self._table_name,
            write_disposition=self._write_disposition,
        )

    async def consume_async(
        self, event: CloudEventEnvelope | Event | dict[str, Any]
    ) -> Any:
        """Asynchronously consume an event into the micro-batch buffer."""
        return await asyncio.to_thread(self.consume, event)

    async def flush_async(self) -> Any:
        """Asynchronously flush buffered events to the lakehouse."""
        return await asyncio.to_thread(self.flush)


def dlt_event_source(
    events: Sequence[CloudEventEnvelope | Event | dict[str, Any]],
    table_name: str = "events",
    name: str = "hexastack_event_source",
) -> Any:
    """Create a standalone dlt.source generator from a sequence of events.

    Args:
        events: Event sequence to stream.
        table_name: Target resource/table name.
        name: Source generator name.

    Returns:
        A dlt.source instance ready for execution in custom pipelines.
    """
    dlt_mod = _require_dlt()

    @dlt_mod.source(name=name)
    def _source() -> Any:
        @dlt_mod.resource(name=table_name, write_disposition="append")
        def _resource() -> Iterable[dict[str, Any]]:
            for e in events:
                yield _normalize_event(e)

        return _resource()

    return _source()


def dlt_outbox_source(
    records: Sequence[OutboxRecord],
    table_name: str = "outbox_records",
    name: str = "hexastack_outbox_source",
) -> Any:
    """Create a standalone dlt.source generator from transactional outbox records.

    Args:
        records: Outbox records sequence.
        table_name: Target resource/table name.
        name: Source generator name.

    Returns:
        A dlt.source instance ready for execution.
    """
    dlt_mod = _require_dlt()

    @dlt_mod.source(name=name)
    def _source() -> Any:
        @dlt_mod.resource(
            name=table_name,
            write_disposition="append",
            primary_key="record_id",
        )
        def _resource() -> Iterable[dict[str, Any]]:
            for r in records:
                yield _normalize_event(r)

        return _resource()

    return _source()


__all__ = [
    "dlt_event_source",
    "dlt_outbox_source",
    "DltEventSink",
    "DltProjectionConsumer",
]
