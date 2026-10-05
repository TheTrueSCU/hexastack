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


def test_streams_memory_slots():
    """Verify StreamMessage and StreamPartitionOffset leverage __slots__."""
    msg = StreamMessage(stream="orders", partition=0, sequence=1, payload={})
    has_msg_dict = hasattr(msg, "__dict__")
    assert has_msg_dict is False
    has_msg_slots = hasattr(msg, "__slots__")
    assert has_msg_slots is True

    offset = StreamPartitionOffset(consumer_group="cg", stream="orders", partition=0)
    has_offset_dict = hasattr(offset, "__dict__")
    assert has_offset_dict is False
    has_offset_slots = hasattr(offset, "__slots__")
    assert has_offset_slots is True
