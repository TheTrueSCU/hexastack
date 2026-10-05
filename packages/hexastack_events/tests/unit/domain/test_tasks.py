"""Unit tests for domain task models and lifecycle state machine."""

import time

from hexastack_events.domain.tasks import TaskRecord, TaskState


def test_task_record_initial_state():
    """Verify default fields of a new task record."""
    task = TaskRecord(
        task_name="send_email",
        payload={"to": "user@example.com"},
        priority=10,
    )
    assert task.task_name == "send_email"
    assert task.payload == {"to": "user@example.com"}
    assert task.priority == 10
    assert task.state == TaskState.PENDING
    assert task.attempts == 0
    assert task.lease_owner is None
    assert task.lease_expires_at is None
    assert task.completed_at is None


def test_task_lease_lifecycle():
    """Verify acquiring and renewing worker lease."""
    task = TaskRecord(task_name="compute", payload={})

    # Acquire lease
    res_acquire = task.acquire_lease("worker-1", lease_duration_seconds=5.0)
    assert res_acquire is True
    assert task.state == TaskState.LEASED
    assert task.lease_owner == "worker-1"
    assert task.attempts == 1
    assert task.lease_expires_at is not None

    # Another worker cannot acquire active lease
    res_other = task.acquire_lease("worker-2", lease_duration_seconds=5.0)
    assert res_other is False
    assert task.lease_owner == "worker-1"

    # Same worker can renew
    res_renew = task.acquire_lease("worker-1", lease_duration_seconds=10.0)
    assert res_renew is True
    assert task.lease_owner == "worker-1"

    # Complete task
    task.complete()
    assert task.state == TaskState.COMPLETED
    assert task.completed_at is not None
    assert task.lease_owner is None
    assert task.lease_expires_at is None


def test_task_lease_expiration_and_takeover():
    """Verify expired lease allows another worker takeover."""
    task = TaskRecord(task_name="process", payload={})
    res = task.acquire_lease("worker-1", lease_duration_seconds=0.1)
    assert res is True

    # Simulate time passing
    future_time = time.time() + 1.0
    expired = task.is_lease_expired(current_time=future_time)
    assert expired is True

    # Worker 2 acquires expired task
    task.lease_expires_at = time.time() - 1.0  # Force expiry in real time
    res2 = task.acquire_lease("worker-2", lease_duration_seconds=5.0)
    assert res2 is True
    assert task.lease_owner == "worker-2"
    assert task.attempts == 2


def test_task_fail_and_dead_letter():
    """Verify retry attempts and dead letter transition on exhaustion."""
    task = TaskRecord(task_name="failing_job", payload={}, max_attempts=2)

    # Attempt 1
    task.acquire_lease("worker-1", 5.0)
    task.fail("Connection error")
    assert task.state == TaskState.PENDING
    assert task.last_error == "Connection error"
    assert task.lease_owner is None

    # Attempt 2
    task.acquire_lease("worker-1", 5.0)
    task.fail("Permanent error")
    assert task.state == TaskState.DEAD_LETTERED
    assert task.last_error == "Permanent error"
