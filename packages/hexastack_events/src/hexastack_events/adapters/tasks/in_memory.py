"""Canonical In-Memory distributed background task queue and worker leasing adapter.

Notes/Architectural Intent:
    Thread-safe and asyncio-safe task queue supporting active worker leasing,
    configurable lease durations, heartbeat renewals, priority-ordered leasing,
    and automatic dead-letter routing upon retry exhaustion.
    Zero external dependencies.
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

from hexastack_events.domain.tasks import TaskRecord, TaskState
from hexastack_events.ports.tasks import AsyncTaskQueuePort, TaskQueuePort


class InMemoryTaskQueueAdapter(TaskQueuePort, AsyncTaskQueuePort):
    """In-memory task queue implementation with worker leasing and priority routing."""

    def __init__(self) -> None:
        """Initialize in-memory task queue storage."""
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = threading.RLock()
        self._async_lock = asyncio.Lock()

    def enqueue(
        self,
        task_name: str,
        payload: dict[str, Any],
        partition_key: str | None = None,
        priority: int = 0,
        max_attempts: int = 3,
    ) -> TaskRecord:
        """Enqueue a background task.

        Args:
            task_name: Task handler/function name.
            payload: Input parameters.
            partition_key: Optional partition key for ordered worker routing.
            priority: Task priority (higher runs first).
            max_attempts: Maximum retry attempts before dead-lettering.

        Returns:
            The created TaskRecord.
        """
        with self._lock:
            record = TaskRecord(
                task_name=task_name,
                payload=payload,
                partition_key=partition_key,
                priority=priority,
                max_attempts=max_attempts,
            )
            self._tasks[record.id] = record
            return record

    def lease_next(
        self,
        worker_id: str,
        task_names: list[str] | None = None,
        lease_duration_seconds: float = 30.0,
    ) -> TaskRecord | None:
        """Acquire a lease on the next available task.

        Args:
            worker_id: Unique worker agent identifier.
            task_names: Optional filter for specific task names.
            lease_duration_seconds: Time before lease expires if not renewed.

        Returns:
            Leased TaskRecord or None if no tasks are available.
        """
        with self._lock:
            now = time.time()
            candidates: list[TaskRecord] = []

            for task in self._tasks.values():
                if task_names is not None and task.task_name not in task_names:
                    continue

                if (
                    task.state == TaskState.PENDING
                    or task.state == TaskState.LEASED
                    and task.is_lease_expired(now)
                ):
                    candidates.append(task)

            if not candidates:
                return None

            # Sort by priority descending (higher first), then created_at ascending (FIFO)
            candidates.sort(key=lambda t: (-t.priority, t.created_at))
            selected = candidates[0]

            leased = selected.acquire_lease(worker_id, lease_duration_seconds)
            if leased:
                return selected
            return None

    def complete(self, task_id: str) -> None:
        """Mark a leased task as successfully completed.

        Args:
            task_id: Task record ID.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is not None:
                task.complete()

    def fail(self, task_id: str, error: str) -> None:
        """Record a failure for a leased task, dead-lettering if attempts exceeded.

        Args:
            task_id: Task record ID.
            error: Error message/traceback string.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is not None:
                task.fail(error)

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
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            return task.acquire_lease(worker_id, lease_duration_seconds)

    async def enqueue_async(
        self,
        task_name: str,
        payload: dict[str, Any],
        partition_key: str | None = None,
        priority: int = 0,
        max_attempts: int = 3,
    ) -> TaskRecord:
        """Enqueue a task asynchronously."""
        async with self._async_lock:
            return self.enqueue(
                task_name=task_name,
                payload=payload,
                partition_key=partition_key,
                priority=priority,
                max_attempts=max_attempts,
            )

    async def lease_next_async(
        self,
        worker_id: str,
        task_names: list[str] | None = None,
        lease_duration_seconds: float = 30.0,
    ) -> TaskRecord | None:
        """Acquire a lease asynchronously."""
        async with self._async_lock:
            return self.lease_next(
                worker_id=worker_id,
                task_names=task_names,
                lease_duration_seconds=lease_duration_seconds,
            )

    async def complete_async(self, task_id: str) -> None:
        """Complete a task asynchronously."""
        async with self._async_lock:
            self.complete(task_id)

    async def fail_async(self, task_id: str, error: str) -> None:
        """Fail a task attempt asynchronously."""
        async with self._async_lock:
            self.fail(task_id, error)

    async def renew_lease_async(
        self,
        task_id: str,
        worker_id: str,
        lease_duration_seconds: float = 30.0,
    ) -> bool:
        """Renew task lease asynchronously."""
        async with self._async_lock:
            return self.renew_lease(
                task_id=task_id,
                worker_id=worker_id,
                lease_duration_seconds=lease_duration_seconds,
            )


__all__ = [
    "InMemoryTaskQueueAdapter",
]
