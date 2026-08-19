from datetime import UTC, datetime

from hexastack_core.adapters.clock import FrozenClock, InMemoryClock


def test_frozen_clock_advance_and_set():
    start = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    clock = FrozenClock(initial_time=start)

    assert clock.now_utc() == start
    assert clock.timestamp() == start.timestamp()

    # Advance 1 hour and 30 minutes
    new_time = clock.advance(hours=1, minutes=30)
    assert new_time == datetime(2026, 1, 1, 13, 30, 0, tzinfo=UTC)
    assert clock.now_utc() == new_time

    # Explicit set
    target = datetime(2027, 5, 20, 0, 0, 0, tzinfo=UTC)
    clock.set_time(target)
    assert clock.now_utc() == target


def test_in_memory_clock():
    clock = InMemoryClock()
    now = clock.now_utc()
    ts = clock.timestamp()

    assert now.tzinfo == UTC
    assert ts > 0
