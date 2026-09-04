"""Domain entities and value objects for distributed partitioned event streams.

Notes/Architectural Intent:
    Defines the core domain primitives for partitioned message streams,
    deterministic partition key mapping, and consumer group offset tracking.
    Strictly zero external dependencies.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StreamMessage:
    """Represents an immutable, sequenced message in a distributed partition stream.

    Notes/Architectural Intent:
        Partition key determines ordered stream placement.
        Sequence number guarantees total ordering within a single partition.
    """

    stream: str
    partition: int
    sequence: int
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    partition_key: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class StreamPartitionOffset:
    """Tracks consumer group progress and acked offsets on a stream partition."""

    consumer_group: str
    stream: str
    partition: int
    last_acked_sequence: int = -1
    updated_at: float = field(default_factory=time.time)
