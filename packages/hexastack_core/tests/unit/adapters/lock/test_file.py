import tempfile
from pathlib import Path

import pytest

from hexastack_core.adapters.lock.file import (
    AsyncFileLockAdapter,
    FileLockAdapter,
)
from hexastack_core.domain.exceptions import LockError


def test_file_lock_adapter_sync_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = Path(tmpdir) / "test.lock"
        lock1 = FileLockAdapter(lock_file, timeout=1.0)
        lock2 = FileLockAdapter(lock_file, timeout=0.1)

        assert lock1.locked() is False

        # Acquire lock1
        assert lock1.acquire() is True
        assert lock1.locked() is True

        # Lock2 non-blocking acquire fails
        assert lock2.acquire(blocking=False) is False
        assert lock2.locked() is False

        # Lock2 timeout acquire fails
        assert lock2.acquire(blocking=True, timeout=0.05) is False

        # Release lock1
        lock1.release()
        assert lock1.locked() is False

        # Now lock2 can acquire
        assert lock2.acquire() is True
        assert lock2.locked() is True
        lock2.release()
        assert lock2.locked() is False


def test_file_lock_adapter_context_manager():
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = Path(tmpdir) / "cm.lock"
        lock = FileLockAdapter(lock_file)

        with lock:
            assert lock.locked() is True

        assert lock.locked() is False


@pytest.mark.anyio
async def test_async_file_lock_adapter_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = Path(tmpdir) / "async.lock"
        lock1 = AsyncFileLockAdapter(lock_file, timeout=1.0)
        lock2 = AsyncFileLockAdapter(lock_file, timeout=0.1)

        assert await lock1.locked() is False

        assert await lock1.acquire() is True
        assert await lock1.locked() is True

        # Lock2 non-blocking acquire fails
        assert await lock2.acquire(blocking=False) is False

        await lock1.release()
        assert await lock1.locked() is False

        # Async context manager
        async with lock2:
            assert await lock2.locked() is True

        assert await lock2.locked() is False


def test_file_lock_adapter_errors(monkeypatch):
    import sys
    from unittest.mock import MagicMock

    from hexastack_core.domain.exceptions import MissingDependencyError

    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = Path(tmpdir) / "err.lock"
        lock = FileLockAdapter(lock_file)

        # Mock acquire unexpected exception
        mock_fl = MagicMock()
        mock_fl.acquire.side_effect = PermissionError("Permission denied")
        lock._lock = mock_fl

        with pytest.raises(LockError, match="Failed to acquire file lock"):
            lock.acquire()

        # Mock release unexpected exception
        mock_fl.release.side_effect = OSError("Disk failure")
        with pytest.raises(LockError, match="Failed to release file lock"):
            lock.release()

    # Test MissingDependencyError
    monkeypatch.setitem(sys.modules, "filelock", None)
    with pytest.raises(MissingDependencyError):
        FileLockAdapter("/tmp/fail.lock")
