"""Canonical In-Memory partitioned stream adapter.

Notes/Architectural Intent:
    High-performance thread-safe in-memory stream buffer implementing StreamPort and AsyncStreamPort.
    Supports deterministic MurmurHash-like partition routing and consumer group tracking.
    Zero external dependencies.
"""

from __future__ import annotations

import asyncio
import hashlib
import threading
from collections import defaultdict
from typing import Any

from hexastack_events.domain.streams import StreamMessage, StreamPartitionOffset
from hexastack_events.ports.streams import AsyncStreamPort, StreamPort


def _hash_partition(key: str, num_partitions: int) -> int:
    """Deterministic hash mapping partition key to partition index."""
    if num_partitions <= 1:
        return 0
    digest = hashlib.md5(key.encode("utf-8"), usedforsecurity=False).hexdigest()
    return int(digest[:8], 16) % num_partitions


class InMemoryStreamAdapter(StreamPort, AsyncStreamPort):
    """Thread-safe and asyncio-safe in-memory partitioned stream adapter."""

    def __init__(self, default_partitions: int = 4) -> None:
        """Initialize in-memory stream adapter.

        Args:
            default_partitions: Default number of partitions per stream.
        """
        self._default_partitions = max(1, default_partitions)
        # stream -> partition_idx -> list[StreamMessage]
        self._streams: dict[str, dict[int, list[StreamMessage]]] = defaultdict(
            lambda: defaultdict(list)
        )
        # consumer_group -> (stream, partition) -> last_acked_sequence
        self._offsets: dict[str, dict[tuple[str, int], int]] = defaultdict(dict)
        self._lock = threading.RLock()
        self._async_lock = asyncio.Lock()

    def publish(
        self,
        stream: str,
        payload: dict[str, Any],
        partition_key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> StreamMessage:
        """Publish a message to a stream with deterministic partition routing."""
        with self._lock:
            partition = (
                _hash_partition(partition_key, self._default_partitions)
                if partition_key is not None
                else 0
            )
            partition_queue = self._streams[stream][partition]
            sequence = len(partition_queue)

            msg = StreamMessage(
                stream=stream,
                partition=partition,
                sequence=sequence,
                payload=payload,
                partition_key=partition_key,
                headers=headers or {},
            )
            partition_queue.append(msg)
            return msg

    def read_partition(
        self,
        stream: str,
        partition: int,
        from_sequence: int = 0,
        batch_size: int = 100,
    ) -> list[StreamMessage]:
        """Read a slice of sequenced messages directly from a specific partition."""
        with self._lock:
            partition_queue = self._streams[stream][partition]
            start = max(0, from_sequence)
            end = start + max(1, batch_size)
            return list(partition_queue[start:end])

    def ack(
        self,
        consumer_group: str,
        stream: str,
        partition: int,
        sequence: int,
    ) -> None:
        """Acknowledge processing of a sequence offset for a consumer group."""
        with self._lock:
            current = self._offsets[consumer_group].get((stream, partition), -1)
            if sequence > current:
                self._offsets[consumer_group][(stream, partition)] = sequence

    def get_offset(
        self,
        consumer_group: str,
        stream: str,
        partition: int,
    ) -> StreamPartitionOffset:
        """Get the current committed offset for a consumer group on a partition."""
        with self._lock:
            seq = self._offsets[consumer_group].get((stream, partition), -1)
            return StreamPartitionOffset(
                consumer_group=consumer_group,
                stream=stream,
                partition=partition,
                last_acked_sequence=seq,
            )

    async def publish_async(
        self,
        stream: str,
        payload: dict[str, Any],
        partition_key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> StreamMessage:
        """Publish a message to a stream asynchronously."""
        async with self._async_lock:
            return self.publish(stream, payload, partition_key, headers)

    async def read_partition_async(
        self,
        stream: str,
        partition: int,
        from_sequence: int = 0,
        batch_size: int = 100,
    ) -> list[StreamMessage]:
        """Read messages from a partition asynchronously."""
        async with self._async_lock:
            return self.read_partition(stream, partition, from_sequence, batch_size)

    async def ack_async(
        self,
        consumer_group: str,
        stream: str,
        partition: int,
        sequence: int,
    ) -> None:
        """Acknowledge processing offset asynchronously."""
        async with self._async_lock:
            self.ack(consumer_group, stream, partition, sequence)

    async def get_offset_async(
        self,
        consumer_group: str,
        stream: str,
        partition: int,
    ) -> StreamPartitionOffset:
        """Get committed partition offset asynchronously."""
        async with self._async_lock:
            return self.get_offset(consumer_group, stream, partition)


__all__ = [
    "InMemoryStreamAdapter",
]
