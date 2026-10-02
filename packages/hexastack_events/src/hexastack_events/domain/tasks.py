"""Domain entities and state machine for distributed background tasks and leases.

Notes/Architectural Intent:
    Defines task records, lifecycle state transitions (PENDING, LEASED, COMPLETED,
    FAILED, DEAD_LETTERED), worker leases, retry limits, and dead-letter routing.
    Strictly zero external dependencies.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TaskState(StrEnum):
    """Lifecycle state of a distributed task within the queue."""

    PENDING = "PENDING"
    LEASED = "LEASED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD_LETTERED = "DEAD_LETTERED"


@dataclass
class TaskRecord:
    """Represents an asynchronous background task record with lease tracking.

    Notes/Architectural Intent:
        Supports distributed active-worker leasing with automatic timeout expiry,
        retry attempts, and dead-letter routing upon exceeding max attempts.
    """

    task_name: str
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: TaskState = TaskState.PENDING
    partition_key: str | None = None
    priority: int = 0
    attempts: int = 0
    max_attempts: int = 3
    lease_owner: str | None = None
    lease_expires_at: float | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    last_error: str | None = None

    def is_lease_expired(self, current_time: float | None = None) -> bool:
        """Check if the current task lease has expired."""
        now = current_time if current_time is not None else time.time()
        if self.state == TaskState.LEASED and self.lease_expires_at is not None:
            return now >= self.lease_expires_at
        return False

    def acquire_lease(self, owner: str, lease_duration_seconds: float) -> bool:
        """Attempt to acquire or renew a lease for a specific worker."""
        now = time.time()
        if self.state == TaskState.PENDING or (
            self.state == TaskState.LEASED and self.is_lease_expired(now)
        ):
            self.state = TaskState.LEASED
            self.lease_owner = owner
            self.lease_expires_at = now + max(0.1, lease_duration_seconds)
            self.attempts += 1
            return True
        if self.state == TaskState.LEASED and self.lease_owner == owner:
            # Renew existing lease
            self.lease_expires_at = now + max(0.1, lease_duration_seconds)
            return True
        return False

    def complete(self) -> None:
        """Mark task as successfully completed."""
        self.state = TaskState.COMPLETED
        self.completed_at = time.time()
        self.lease_owner = None
        self.lease_expires_at = None

    def fail(self, error: str) -> None:
        """Mark task attempt as failed, dead-lettering if max attempts exhausted."""
        self.last_error = error
        self.lease_owner = None
        self.lease_expires_at = None

        if self.attempts >= self.max_attempts:
            self.state = TaskState.DEAD_LETTERED
        else:
            self.state = TaskState.PENDING
