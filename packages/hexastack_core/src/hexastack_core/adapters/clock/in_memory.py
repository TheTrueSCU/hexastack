from datetime import UTC, datetime, timedelta

from hexastack_core.ports.clock import ClockPort


class InMemoryClock(ClockPort):
    """Real-time clock adapter reading system UTC time.

    Notes/Architectural Intent:
        Default production/local adapter providing real-time clock access.
    """

    def now_utc(self) -> datetime:
        """Return the current UTC datetime."""
        return datetime.now(UTC)

    def timestamp(self) -> float:
        """Return the current POSIX timestamp."""
        return datetime.now(UTC).timestamp()


class FrozenClock(ClockPort):
    """Deterministic simulated clock supporting time freezing and manual advancement.

    Notes/Architectural Intent:
        Allows test cases to freeze time at a fixed point and advance it explicitly
        (e.g., clock.advance(minutes=10)) to verify TTL expiration and timeout logic.
    """

    def __init__(self, initial_time: datetime | None = None) -> None:
        """Initialize FrozenClock.

        Args:
            initial_time: Optional datetime to start at. Defaults to current UTC time.
        """
        self._current_time: datetime = (
            initial_time.astimezone(UTC)
            if initial_time is not None
            else datetime.now(UTC)
        )

    def advance(
        self,
        seconds: float = 0,
        minutes: float = 0,
        hours: float = 0,
        days: float = 0,
    ) -> datetime:
        """Advance the frozen clock forward by a specified duration.

        Args:
            seconds: Seconds to advance.
            minutes: Minutes to advance.
            hours: Hours to advance.
            days: Days to advance.

        Returns:
            The new current UTC datetime after advancement.
        """
        delta = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        self._current_time += delta
        return self._current_time

    def now_utc(self) -> datetime:
        """Return the frozen UTC datetime."""
        return self._current_time

    def set_time(self, new_time: datetime) -> None:
        """Set the frozen clock to an explicit datetime."""
        self._current_time = new_time.astimezone(UTC)

    def timestamp(self) -> float:
        """Return the frozen POSIX timestamp."""
        return self._current_time.timestamp()


__all__ = [
    "FrozenClock",
    "InMemoryClock",
]
