"""Unit tests for abstract task queue ports."""

import pytest

from hexastack_events.ports.tasks import AsyncTaskQueuePort, TaskQueuePort


def test_abstract_task_queue_port_cannot_be_instantiated():
    """Verify TaskQueuePort cannot be instantiated directly."""
    with pytest.raises(TypeError):
        TaskQueuePort()  # type: ignore[abstract]


def test_abstract_async_task_queue_port_cannot_be_instantiated():
    """Verify AsyncTaskQueuePort cannot be instantiated directly."""
    with pytest.raises(TypeError):
        AsyncTaskQueuePort()  # type: ignore[abstract]
