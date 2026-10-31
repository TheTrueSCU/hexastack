"""Unit tests for abstract task queue ports."""

import inspect

import pytest

from hexastack_events.ports.tasks import AsyncTaskQueuePort, TaskQueuePort


def test_abstract_task_queue_port_cannot_be_instantiated():
    """Verify TaskQueuePort cannot be instantiated directly."""
    with pytest.raises(TypeError):
        TaskQueuePort()  # ty: ignore[call-non-callable]


def test_abstract_async_task_queue_port_cannot_be_instantiated():
    """Verify AsyncTaskQueuePort cannot be instantiated directly."""
    with pytest.raises(TypeError):
        AsyncTaskQueuePort()  # ty: ignore[call-non-callable]


def test_task_queue_port_is_abstract() -> None:
    """Verify that TaskQueuePort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(TaskQueuePort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        TaskQueuePort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_task_queue_port_abstract_methods() -> None:
    """Verify abstract methods on TaskQueuePort."""
    expected = {"complete", "enqueue", "fail", "lease_next", "renew_lease"}
    abstracts = TaskQueuePort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


def test_async_task_queue_port_is_abstract() -> None:
    """Verify that AsyncTaskQueuePort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(AsyncTaskQueuePort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        AsyncTaskQueuePort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_async_task_queue_port_abstract_methods() -> None:
    """Verify abstract methods on AsyncTaskQueuePort."""
    expected = {
        "complete_async",
        "enqueue_async",
        "fail_async",
        "lease_next_async",
        "renew_lease_async",
    }
    abstracts = AsyncTaskQueuePort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
