from datetime import UTC, datetime

from hexastack_core.adapters.clock import FrozenClock
from hexastack_core.ports.clock import ClockPort


def test_clock_port_contract():
    target = datetime(2026, 8, 15, 10, 0, 0, tzinfo=UTC)
    clock: ClockPort = FrozenClock(target)

    assert clock.now_utc() == target
    assert clock.timestamp() == target.timestamp()
