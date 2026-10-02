"""Unit tests for InMemoryStreamAdapter."""

import pytest

from hexastack_events.adapters.streams.in_memory import InMemoryStreamAdapter


def test_publish_and_partition_routing():
    """Verify deterministic partition assignment."""
    adapter = InMemoryStreamAdapter(default_partitions=4)

    msg1 = adapter.publish("telemetry", {"temp": 21.5}, partition_key="sensor_a")
    msg2 = adapter.publish("telemetry", {"temp": 22.0}, partition_key="sensor_a")
    msg3 = adapter.publish("telemetry", {"temp": 19.0}, partition_key="sensor_b")

    # Same partition key routes to identical partition
    assert msg1.partition == msg2.partition
    assert msg1.sequence == 0
    assert msg2.sequence == 1
    assert msg3.sequence == 0

    # Read partition
    partition_msgs = adapter.read_partition("telemetry", partition=msg1.partition)
    assert len(partition_msgs) == 2
    assert partition_msgs[0].payload == {"temp": 21.5}
    assert partition_msgs[1].payload == {"temp": 22.0}


def test_ack_and_offset_tracking():
    """Verify consumer group offset progression."""
    adapter = InMemoryStreamAdapter(default_partitions=2)

    # Initial offset
    offset = adapter.get_offset("analytics_group", "events", partition=0)
    assert offset.last_acked_sequence == -1

    # Acknowledge sequence 5
    adapter.ack("analytics_group", "events", partition=0, sequence=5)
    offset = adapter.get_offset("analytics_group", "events", partition=0)
    assert offset.last_acked_sequence == 5

    # Out-of-order lower ack does not regress offset
    adapter.ack("analytics_group", "events", partition=0, sequence=3)
    offset = adapter.get_offset("analytics_group", "events", partition=0)
    assert offset.last_acked_sequence == 5


@pytest.mark.asyncio
async def test_async_stream_operations():
    """Verify async publish, read, and ack operations."""
    adapter = InMemoryStreamAdapter(default_partitions=2)

    msg = await adapter.publish_async("logs", {"level": "info"}, partition_key="srv-1")
    assert msg.stream == "logs"

    messages = await adapter.read_partition_async("logs", partition=msg.partition)
    assert len(messages) == 1
    assert messages[0].payload == {"level": "info"}

    await adapter.ack_async(
        "log_collector", "logs", partition=msg.partition, sequence=0
    )
    offset = await adapter.get_offset_async(
        "log_collector", "logs", partition=msg.partition
    )
    assert offset.last_acked_sequence == 0
