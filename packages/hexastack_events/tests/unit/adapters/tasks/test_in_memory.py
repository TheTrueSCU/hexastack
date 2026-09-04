"""Unit tests for InMemoryTaskQueueAdapter."""

import pytest

from hexastack_events.adapters.tasks.in_memory import InMemoryTaskQueueAdapter
from hexastack_events.domain.tasks import TaskState


def test_enqueue_and_priority_leasing():
    """Verify priority-ordered task leasing."""
    queue = InMemoryTaskQueueAdapter()

    # Enqueue low and high priority tasks
    task_low = queue.enqueue("process_data", {"val": 1}, priority=1)
    task_high = queue.enqueue("process_data", {"val": 2}, priority=10)

    # First lease gets high priority task
    leased_1 = queue.lease_next("worker-1", task_names=["process_data"])
    assert leased_1 is not None
    assert leased_1.id == task_high.id
    assert leased_1.lease_owner == "worker-1"

    # Second lease gets low priority task
    leased_2 = queue.lease_next("worker-2", task_names=["process_data"])
    assert leased_2 is not None
    assert leased_2.id == task_low.id

    # No more available tasks
    leased_none = queue.lease_next("worker-3")
    assert leased_none is None


def test_complete_and_fail_flow():
    """Verify complete, fail, and retry handling."""
    queue = InMemoryTaskQueueAdapter()
    task = queue.enqueue("send_notification", {"msg": "hello"}, max_attempts=2)

    leased = queue.lease_next("worker-1")
    assert leased is not None

    # Fail first attempt -> goes back to PENDING
    queue.fail(task.id, "Gateway timeout")
    assert task.state == TaskState.PENDING
    assert task.attempts == 1

    # Lease again and complete
    leased_again = queue.lease_next("worker-2")
    assert leased_again is not None
    assert leased_again.id == task.id

    queue.complete(task.id)
    assert task.state == TaskState.COMPLETED


def test_renew_lease():
    """Verify renewing active leases."""
    queue = InMemoryTaskQueueAdapter()
    task = queue.enqueue("long_job", {})

    queue.lease_next("worker-1", lease_duration_seconds=5.0)

    # Worker 1 renews
    renewed = queue.renew_lease(task.id, "worker-1", lease_duration_seconds=10.0)
    assert renewed is True

    # Worker 2 cannot renew Worker 1's lease
    renew_invalid = queue.renew_lease(task.id, "worker-2", lease_duration_seconds=10.0)
    assert renew_invalid is False


@pytest.mark.asyncio
async def test_async_task_queue_operations():
    """Verify async enqueue, lease, complete, fail, and renew."""
    queue = InMemoryTaskQueueAdapter()

    task = await queue.enqueue_async("async_job", {"x": 42}, priority=5)
    assert task.task_name == "async_job"

    leased = await queue.lease_next_async("worker-async")
    assert leased is not None
    assert leased.id == task.id

    renewed = await queue.renew_lease_async(task.id, "worker-async", 15.0)
    assert renewed is True

    await queue.complete_async(task.id)
    assert task.state == TaskState.COMPLETED
