"""Distributed Hexaqueue task queue and active worker leasing adapter.

Notes/Architectural Intent:
    Connects Hexastack applications to a remote Hexaqueue distributed task scheduling
    cluster via standard HTTP/REST endpoints (/api/v1/jobs, /api/v1/runs).
    Maintains zero hard dependencies on Hexaqueue server or worker packages,
    guaranteeing strict architectural separation between coordinator and consumer nodes.
"""

from __future__ import annotations

import time
from typing import Any

from hexastack_core.utils.imports import require_dependency
from hexastack_events.domain.tasks import TaskRecord, TaskState
from hexastack_events.ports.tasks import AsyncTaskQueuePort, TaskQueuePort

__all__ = [
    "HexaqueueTaskQueueAdapter",
]


class HexaqueueTaskQueueAdapter(TaskQueuePort, AsyncTaskQueuePort):
    """Distributed task queue adapter communicating with Hexaqueue via HTTP/REST."""

    def __init__(
        self,
        cluster_url: str = "http://localhost:8000",
        token: str | None = None,
        default_queue: str = "default",
        client: Any | None = None,
        async_client: Any | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        """Initialize HexaqueueTaskQueueAdapter.

        Args:
            cluster_url: Base URL of the remote Hexaqueue cluster.
            token: Optional bearer authentication token.
            default_queue: Target queue partition name.
            client: Optional pre-configured synchronous HTTP client (httpx.Client).
            async_client: Optional pre-configured asynchronous HTTP client (httpx.AsyncClient).
            timeout_seconds: Request timeout in seconds.

        Raises:
            MissingDependencyError: If httpx is not installed.
        """
        httpx = require_dependency(
            "httpx",
            extra="hexaqueue",
            package="hexastack-events",
            feature_name="HexaqueueTaskQueueAdapter",
        )

        self._cluster_url = cluster_url.rstrip("/")
        self._token = token
        self._default_queue = default_queue
        self._timeout = timeout_seconds

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"

        self._client = client or httpx.Client(
            base_url=self._cluster_url,
            headers=headers,
            timeout=timeout_seconds,
        )
        self._async_client = async_client or httpx.AsyncClient(
            base_url=self._cluster_url,
            headers=headers,
            timeout=timeout_seconds,
        )

    def _parse_task_record(self, data: dict[str, Any]) -> TaskRecord:
        """Parse raw JSON cluster response into a domain TaskRecord entity."""
        state_str = str(data.get("state", TaskState.PENDING.value))
        try:
            state = TaskState(state_str)
        except ValueError:
            state = TaskState.PENDING

        return TaskRecord(
            id=str(data.get("id", "")),
            task_name=str(data.get("task_name", "")),
            payload=data.get("payload", {}),
            state=state,
            partition_key=data.get("partition_key"),
            priority=int(data.get("priority", 0)),
            attempts=int(data.get("attempts", 0)),
            max_attempts=int(data.get("max_attempts", 3)),
            lease_owner=data.get("lease_owner"),
            lease_expires_at=data.get("lease_expires_at"),
            created_at=float(data.get("created_at", time.time())),
            completed_at=data.get("completed_at"),
            last_error=data.get("last_error"),
        )

    def enqueue(
        self,
        task_name: str,
        payload: dict[str, Any],
        partition_key: str | None = None,
        priority: int = 0,
        max_attempts: int = 3,
    ) -> TaskRecord:
        """Enqueue a background task into Hexaqueue.

        Args:
            task_name: Task handler/function name.
            payload: Input parameters.
            partition_key: Optional partition key for ordered worker routing.
            priority: Task priority (higher runs first).
            max_attempts: Maximum retry attempts before dead-lettering.

        Returns:
            The created TaskRecord.
        """
        body = {
            "task_name": task_name,
            "payload": payload,
            "partition_key": partition_key,
            "priority": priority,
            "max_attempts": max_attempts,
            "queue": self._default_queue,
        }
        resp = self._client.post("/api/v1/jobs", json=body)
        resp.raise_for_status()
        data = resp.json()
        return self._parse_task_record(data)

    def lease_next(
        self,
        worker_id: str,
        task_names: list[str] | None = None,
        lease_duration_seconds: float = 30.0,
    ) -> TaskRecord | None:
        """Acquire a lease on the next available task from Hexaqueue.

        Args:
            worker_id: Unique worker agent identifier.
            task_names: Optional filter for specific task names.
            lease_duration_seconds: Time before lease expires if not renewed.

        Returns:
            Leased TaskRecord or None if no tasks are available.
        """
        body = {
            "worker_id": worker_id,
            "task_names": task_names,
            "lease_duration_seconds": lease_duration_seconds,
            "queue": self._default_queue,
        }
        resp = self._client.post("/api/v1/jobs/lease", json=body)
        if resp.status_code in (204, 404):
            return None
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        return self._parse_task_record(data)

    def complete(self, task_id: str, worker_id: str | None = None) -> None:
        """Mark a leased task as successfully completed in Hexaqueue.

        Args:
            task_id: Task record ID.
            worker_id: Optional worker identifier to verify lease ownership.
        """
        body = {"worker_id": worker_id}
        resp = self._client.post(f"/api/v1/jobs/{task_id}/complete", json=body)
        if resp.status_code not in (200, 204, 404):
            resp.raise_for_status()

    def fail(self, task_id: str, error: str, worker_id: str | None = None) -> None:
        """Record a failure for a leased task in Hexaqueue.

        Args:
            task_id: Task record ID.
            error: Error message/traceback string.
            worker_id: Optional worker identifier to verify lease ownership.
        """
        body = {"worker_id": worker_id, "error": error}
        resp = self._client.post(f"/api/v1/jobs/{task_id}/fail", json=body)
        if resp.status_code not in (200, 204, 404):
            resp.raise_for_status()

    def renew_lease(
        self,
        task_id: str,
        worker_id: str,
        lease_duration_seconds: float = 30.0,
    ) -> bool:
        """Renew an active lease on a running task in Hexaqueue.

        Args:
            task_id: Task record ID.
            worker_id: Worker currently holding the lease.
            lease_duration_seconds: Additional lease duration.

        Returns:
            True if lease was successfully renewed, False otherwise.
        """
        body = {
            "worker_id": worker_id,
            "lease_duration_seconds": lease_duration_seconds,
        }
        resp = self._client.post(f"/api/v1/jobs/{task_id}/renew", json=body)
        return resp.status_code == 200

    async def enqueue_async(
        self,
        task_name: str,
        payload: dict[str, Any],
        partition_key: str | None = None,
        priority: int = 0,
        max_attempts: int = 3,
    ) -> TaskRecord:
        """Enqueue a background task asynchronously."""
        body = {
            "task_name": task_name,
            "payload": payload,
            "partition_key": partition_key,
            "priority": priority,
            "max_attempts": max_attempts,
            "queue": self._default_queue,
        }
        resp = await self._async_client.post("/api/v1/jobs", json=body)
        resp.raise_for_status()
        data = resp.json()
        return self._parse_task_record(data)

    async def lease_next_async(
        self,
        worker_id: str,
        task_names: list[str] | None = None,
        lease_duration_seconds: float = 30.0,
    ) -> TaskRecord | None:
        """Acquire a lease asynchronously."""
        body = {
            "worker_id": worker_id,
            "task_names": task_names,
            "lease_duration_seconds": lease_duration_seconds,
            "queue": self._default_queue,
        }
        resp = await self._async_client.post("/api/v1/jobs/lease", json=body)
        if resp.status_code in (204, 404):
            return None
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        return self._parse_task_record(data)

    async def complete_async(self, task_id: str, worker_id: str | None = None) -> None:
        """Complete a task asynchronously."""
        body = {"worker_id": worker_id}
        resp = await self._async_client.post(
            f"/api/v1/jobs/{task_id}/complete", json=body
        )
        if resp.status_code not in (200, 204, 404):
            resp.raise_for_status()

    async def fail_async(
        self, task_id: str, error: str, worker_id: str | None = None
    ) -> None:
        """Fail a task attempt asynchronously."""
        body = {"worker_id": worker_id, "error": error}
        resp = await self._async_client.post(f"/api/v1/jobs/{task_id}/fail", json=body)
        if resp.status_code not in (200, 204, 404):
            resp.raise_for_status()

    async def renew_lease_async(
        self,
        task_id: str,
        worker_id: str,
        lease_duration_seconds: float = 30.0,
    ) -> bool:
        """Renew task lease asynchronously."""
        body = {
            "worker_id": worker_id,
            "lease_duration_seconds": lease_duration_seconds,
        }
        resp = await self._async_client.post(f"/api/v1/jobs/{task_id}/renew", json=body)
        return resp.status_code == 200

    def close(self) -> None:
        """Close synchronous HTTP connection pool."""
        self._client.close()

    async def close_async(self) -> None:
        """Close asynchronous HTTP connection pool."""
        await self._async_client.aclose()
