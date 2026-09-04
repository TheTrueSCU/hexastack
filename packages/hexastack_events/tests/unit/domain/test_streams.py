"""Unit tests for domain stream models."""

import time

from hexastack_events.domain.streams import StreamMessage, StreamPartitionOffset


def test_stream_message_creation():
    """Verify StreamMessage initialization and properties."""
    msg = StreamMessage(
        stream="orders",
        partition=2,
        sequence=42,
        payload={"order_id": 123},
        partition_key="user_99",
        headers={"trace_id": "abc"},
    )
    assert msg.stream == "orders"
    assert msg.partition == 2
    assert msg.sequence == 42
    assert msg.payload == {"order_id": 123}
    assert msg.partition_key == "user_99"
    assert msg.headers["trace_id"] == "abc"
    assert msg.id is not None
    assert msg.timestamp <= time.time()


def test_stream_partition_offset_creation():
    """Verify StreamPartitionOffset fields and default sequence."""
    offset = StreamPartitionOffset(
        consumer_group="cg-1",
        stream="orders",
        partition=0,
    )
    assert offset.consumer_group == "cg-1"
    assert offset.stream == "orders"
    assert offset.partition == 0
    assert offset.last_acked_sequence == -1
