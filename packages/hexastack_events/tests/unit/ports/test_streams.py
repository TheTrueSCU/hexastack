"""Unit tests for abstract stream ports."""

import pytest

from hexastack_events.ports.streams import AsyncStreamPort, StreamPort


def test_abstract_stream_port_cannot_be_instantiated():
    """Verify StreamPort cannot be instantiated directly."""
    with pytest.raises(TypeError):
        StreamPort()  # type: ignore[abstract]


def test_abstract_async_stream_port_cannot_be_instantiated():
    """Verify AsyncStreamPort cannot be instantiated directly."""
    with pytest.raises(TypeError):
        AsyncStreamPort()  # type: ignore[abstract]
