"""Unit tests for abstract stream ports."""

import inspect

import pytest

from hexastack_events.ports.streams import AsyncStreamPort, StreamPort


def test_abstract_stream_port_cannot_be_instantiated():
    """Verify StreamPort cannot be instantiated directly."""
    with pytest.raises(TypeError):
        StreamPort()  # ty: ignore[call-non-callable]


def test_abstract_async_stream_port_cannot_be_instantiated():
    """Verify AsyncStreamPort cannot be instantiated directly."""
    with pytest.raises(TypeError):
        AsyncStreamPort()  # ty: ignore[call-non-callable]


def test_stream_port_is_abstract() -> None:
    """Verify that StreamPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(StreamPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        StreamPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_stream_port_abstract_methods() -> None:
    """Verify abstract methods on StreamPort."""
    expected = {"ack", "get_offset", "publish", "read_partition"}
    abstracts = StreamPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


def test_async_stream_port_is_abstract() -> None:
    """Verify that AsyncStreamPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(AsyncStreamPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        AsyncStreamPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_async_stream_port_abstract_methods() -> None:
    """Verify abstract methods on AsyncStreamPort."""
    expected = {
        "ack_async",
        "get_offset_async",
        "publish_async",
        "read_partition_async",
    }
    abstracts = AsyncStreamPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
