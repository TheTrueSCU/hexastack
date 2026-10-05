"""Abstract ports for distributed event stream ingestion and partitioned consumption.

Notes/Architectural Intent:
    Defines the contract for partitioned stream brokers (InMemory, Redis Streams, Kafka/NATS).
    Guarantees FIFO ordering per partition key and consumer group offset management.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from hexastack_events.domain.streams import StreamMessage, StreamPartitionOffset


class StreamPort(ABC):
    """Synchronous abstract port for partitioned event stream operations."""

    @abstractmethod
    def publish(
        self,
        stream: str,
        payload: dict[str, Any],
        partition_key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> StreamMessage:
        """Publish a message to a stream with deterministic partition routing.

        Args:
            stream: Stream topic name.
            payload: JSON/dict message data.
            partition_key: Optional partition key (hashes to determine partition).
            headers: Optional message metadata headers.

        Returns:
            The published, sequenced StreamMessage.
        """

    @abstractmethod
    def read_partition(
        self,
        stream: str,
        partition: int,
        from_sequence: int = 0,
        batch_size: int = 100,
    ) -> list[StreamMessage]:
        """Read a slice of sequenced messages directly from a specific partition.

        Args:
            stream: Stream topic name.
            partition: Partition index.
            from_sequence: Starting sequence number (inclusive).
            batch_size: Maximum messages to retrieve.

        Returns:
            List of sequenced StreamMessages.
        """

    @abstractmethod
    def ack(
        self,
        consumer_group: str,
        stream: str,
        partition: int,
        sequence: int,
    ) -> None:
        """Acknowledge processing of a sequence offset for a consumer group.

        Args:
            consumer_group: Consumer group identifier.
            stream: Stream topic name.
            partition: Partition index.
            sequence: Last processed sequence number.
        """

    @abstractmethod
    def get_offset(
        self,
        consumer_group: str,
        stream: str,
        partition: int,
    ) -> StreamPartitionOffset:
        """Get the current committed offset for a consumer group on a partition.

        Args:
            consumer_group: Consumer group identifier.
            stream: Stream topic name.
            partition: Partition index.

        Returns:
            Current StreamPartitionOffset record.
        """


class AsyncStreamPort(ABC):
    """Asynchronous abstract port for partitioned event stream operations."""

    @abstractmethod
    async def publish_async(
        self,
        stream: str,
        payload: dict[str, Any],
        partition_key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> StreamMessage:
        """Publish a message to a stream asynchronously."""

    @abstractmethod
    async def read_partition_async(
        self,
        stream: str,
        partition: int,
        from_sequence: int = 0,
        batch_size: int = 100,
    ) -> list[StreamMessage]:
        """Read messages from a partition asynchronously."""

    @abstractmethod
    async def ack_async(
        self,
        consumer_group: str,
        stream: str,
        partition: int,
        sequence: int,
    ) -> None:
        """Acknowledge processing offset asynchronously."""

    @abstractmethod
    async def get_offset_async(
        self,
        consumer_group: str,
        stream: str,
        partition: int,
    ) -> StreamPartitionOffset:
        """Get committed partition offset asynchronously."""


__all__ = [
    "AsyncStreamPort",
    "StreamPort",
]
