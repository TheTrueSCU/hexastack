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
