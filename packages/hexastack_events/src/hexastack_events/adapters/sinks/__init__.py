"""Sinks adapters for external analytical and lakehouse storage.

Notes/Architectural Intent:
    Provides export of lakehouse sinks and data sources (such as dlt) for
    analytical projection and event lake ingestion.
"""

from __future__ import annotations

from hexastack_events.adapters.sinks.dlt import (
    DltEventSink,
    DltProjectionConsumer,
    dlt_event_source,
    dlt_outbox_source,
)

__all__ = [
    "dlt_event_source",
    "dlt_outbox_source",
    "DltEventSink",
    "DltProjectionConsumer",
]
