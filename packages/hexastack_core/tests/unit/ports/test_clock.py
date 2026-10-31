import inspect
from datetime import UTC, datetime

import pytest

from hexastack_core.adapters.clock import FrozenClock
from hexastack_core.ports.clock import ClockPort


def test_clock_port_contract():
    target = datetime(2026, 8, 15, 10, 0, 0, tzinfo=UTC)
    clock: ClockPort = FrozenClock(target)

    assert clock.now_utc() == target
    assert clock.timestamp() == target.timestamp()


def test_clock_port_is_abstract() -> None:
    """Verify that ClockPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(ClockPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        ClockPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_clock_port_abstract_methods() -> None:
    """Verify abstract methods on ClockPort."""
    expected = {"now_utc", "timestamp"}
    abstracts = ClockPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
