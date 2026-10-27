"""Unit tests for hermetic clock mocking and freeze_time utilities.

Notes/Architectural Intent:
    Verifies that freeze_time correctly wraps time_machine for synchronous,
    asynchronous, and decorated contexts, and raises actionable errors when missing.
"""

import sys
import time
from datetime import UTC, datetime

import pytest

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_core.testing.clock import freeze_time


def test_freeze_time_sync_context_manager() -> None:
    """Verify freeze_time operates correctly in a synchronous context manager."""
    target_epoch = 1_700_000_000.0

    with freeze_time(target_epoch) as traveller:
        current_time = time.time()
        assert current_time == target_epoch

        traveller.shift(45.0)
        shifted_time = time.time()
        assert shifted_time == target_epoch + 45.0

    # Outside the context manager, time is restored to real clock
    restored_time = time.time()
    assert restored_time > target_epoch


@pytest.mark.anyio
async def test_freeze_time_async_context_manager() -> None:
    """Verify freeze_time operates correctly in an async context manager."""
    target_dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

    async with freeze_time(target_dt) as traveller:
        current_dt = datetime.now(UTC)
        assert current_dt == target_dt

        traveller.shift(120.0)
        shifted_dt = datetime.now(UTC)
        diff_seconds = (shifted_dt - target_dt).total_seconds()
        assert diff_seconds == 120.0


@freeze_time(1_600_000_000.0)
def test_freeze_time_decorator() -> None:
    """Verify freeze_time operates as a test function decorator."""
    current_time = time.time()
    assert current_time == 1_600_000_000.0


def test_freeze_time_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify freeze_time raises MissingDependencyError when time-machine is missing."""
    monkeypatch.setitem(sys.modules, "time_machine", None)

    with pytest.raises(MissingDependencyError, match="hexastack-core\\[testing\\]"):
        freeze_time(100.0)
