import pytest
from hexastack_events.ports.outbox import (
    OutboxRelayPort,
    OutboxStoragePort,
)


def test_outbox_storage_port_abstract():
    with pytest.raises(TypeError):
        OutboxStoragePort()  # type: ignore[abstract]


def test_outbox_relay_port_abstract():
    with pytest.raises(TypeError):
        OutboxRelayPort()  # type: ignore[abstract]
