from datetime import UTC, datetime

from hexastack_core.ports.clock import ClockPort


class MockClock(ClockPort):
    def __init__(self, fixed_time: datetime) -> None:
        self.fixed = fixed_time

    def now_utc(self) -> datetime:
        return self.fixed

    def timestamp(self) -> float:
        return self.fixed.timestamp()


def test_clock_port_contract():
    target = datetime(2026, 8, 15, 10, 0, 0, tzinfo=UTC)
    clock: ClockPort = MockClock(target)

    assert clock.now_utc() == target
    assert clock.timestamp() == target.timestamp()
