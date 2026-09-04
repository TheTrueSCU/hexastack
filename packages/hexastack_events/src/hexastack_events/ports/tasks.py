"""Abstract ports for distributed background task queues and worker leasing.

Notes/Architectural Intent:
    Defines the contract for task queues with active worker leasing,
    heartbeats, retry limits, and dead-letter queue routing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from hexastack_events.domain.tasks import TaskRecord


class TaskQueuePort(ABC):
    """Synchronous abstract port for task queue operations."""

    @abstractmethod
    def enqueue(
        self,
        task_name: str,
        payload: dict[str, Any],
        partition_key: str | None = None,
        priority: int = 0,
        max_attempts: int = 3,
    ) -> TaskRecord:
        """Enqueue a background task for distributed processing.

        Args:
            task_name: Task handler/function name.
            payload: Input parameters.
            partition_key: Optional partition key for ordered worker routing.
            priority: Task priority (higher runs first).
            max_attempts: Maximum retry attempts before dead-lettering.

        Returns:
            The created TaskRecord.
        """

    @abstractmethod
    def lease_next(
        self,
        worker_id: str,
        task_names: list[str] | None = None,
        lease_duration_seconds: float = 30.0,
    ) -> TaskRecord | None:
        """Acquire a lease on the next available task for execution.

        Args:
            worker_id: Unique worker agent identifier.
            task_names: Optional filter for specific task names.
            lease_duration_seconds: Time before lease expires if not renewed.

        Returns:
            Leased TaskRecord or None if no tasks are available.
        """

    @abstractmethod
    def complete(self, task_id: str) -> None:
        """Mark a leased task as successfully completed.

        Args:
            task_id: Task record ID.
        """

    @abstractmethod
    def fail(self, task_id: str, error: str) -> None:
        """Record a failure for a leased task, dead-lettering if attempts exceeded.

        Args:
            task_id: Task record ID.
            error: Error message/traceback string.
        """

    @abstractmethod
    def renew_lease(
        self,
        task_id: str,
        worker_id: str,
        lease_duration_seconds: float = 30.0,
    ) -> bool:
        """Renew an active lease on a running task.

        Args:
            task_id: Task record ID.
            worker_id: Worker currently holding the lease.
            lease_duration_seconds: Additional lease duration.

        Returns:
            True if lease was successfully renewed, False otherwise.
        """


class AsyncTaskQueuePort(ABC):
    """Asynchronous abstract port for task queue operations."""

    @abstractmethod
    async def enqueue_async(
        self,
        task_name: str,
        payload: dict[str, Any],
        partition_key: str | None = None,
        priority: int = 0,
        max_attempts: int = 3,
    ) -> TaskRecord:
        """Enqueue a task asynchronously."""

    @abstractmethod
    async def lease_next_async(
        self,
        worker_id: str,
        task_names: list[str] | None = None,
        lease_duration_seconds: float = 30.0,
    ) -> TaskRecord | None:
        """Acquire a lease asynchronously."""

    @abstractmethod
    async def complete_async(self, task_id: str) -> None:
        """Complete a task asynchronously."""

    @abstractmethod
    async def fail_async(self, task_id: str, error: str) -> None:
        """Fail a task attempt asynchronously."""

    @abstractmethod
    async def renew_lease_async(
        self,
        task_id: str,
        worker_id: str,
        lease_duration_seconds: float = 30.0,
    ) -> bool:
        """Renew task lease asynchronously."""


__all__ = [
    "AsyncTaskQueuePort",
    "TaskQueuePort",
]
