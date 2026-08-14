import pytest

from hexastack_events.ports.buses import DistributedEventBusPort


def test_distributed_event_bus_port_abstract():
    with pytest.raises(TypeError):
        DistributedEventBusPort()  # type: ignore[abstract]
