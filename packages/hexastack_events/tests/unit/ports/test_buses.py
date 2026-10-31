import inspect

import pytest

from hexastack_events.ports.buses import DistributedEventBusPort


def test_distributed_event_bus_port_abstract():
    with pytest.raises(TypeError):
        DistributedEventBusPort()  # ty: ignore[call-non-callable]


def test_distributed_event_bus_port_is_abstract() -> None:
    """Verify that DistributedEventBusPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(DistributedEventBusPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        DistributedEventBusPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_distributed_event_bus_port_abstract_methods() -> None:
    """Verify abstract methods on DistributedEventBusPort."""
    expected = {"publish_envelope", "subscribe"}
    abstracts = DistributedEventBusPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
