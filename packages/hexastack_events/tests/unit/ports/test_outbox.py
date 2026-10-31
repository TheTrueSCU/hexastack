import inspect

import pytest

from hexastack_events.ports.outbox import (
    OutboxRelayPort,
    OutboxStoragePort,
)


def test_outbox_relay_port_abstract():
    with pytest.raises(TypeError):
        OutboxRelayPort()  # ty: ignore[call-non-callable]


def test_outbox_storage_port_abstract():
    with pytest.raises(TypeError):
        OutboxStoragePort()  # ty: ignore[call-non-callable]


def test_outbox_storage_port_is_abstract() -> None:
    """Verify that OutboxStoragePort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(OutboxStoragePort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        OutboxStoragePort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_outbox_storage_port_abstract_methods() -> None:
    """Verify abstract methods on OutboxStoragePort."""
    expected = {"fetch_pending", "mark_failed", "mark_published", "save", "save_all"}
    abstracts = OutboxStoragePort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


def test_outbox_relay_port_is_abstract() -> None:
    """Verify that OutboxRelayPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(OutboxRelayPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        OutboxRelayPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_outbox_relay_port_abstract_methods() -> None:
    """Verify abstract methods on OutboxRelayPort."""
    expected = {"publish_pending_batch", "start", "stop"}
    abstracts = OutboxRelayPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
