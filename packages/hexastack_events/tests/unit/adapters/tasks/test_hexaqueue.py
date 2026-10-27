"""Unit and dual-implementation verification tests for HexaqueueTaskQueueAdapter.

Notes/Architectural Intent:
    Verifies that HexaqueueTaskQueueAdapter correctly coordinates with a Hexaqueue
    HTTP API across both synchronous and asynchronous modes, verifying dual-oracle parity
    against the reference InMemoryTaskQueueAdapter.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import httpx
import pytest

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_events.adapters.tasks.hexaqueue import HexaqueueTaskQueueAdapter
from hexastack_events.adapters.tasks.in_memory import InMemoryTaskQueueAdapter
from hexastack_events.domain.tasks import TaskRecord, TaskState


def _record_to_dict(record: TaskRecord) -> dict[str, Any]:
    """Convert TaskRecord entity to JSON-serializable dictionary."""
    return {
        "id": record.id,
        "task_name": record.task_name,
        "payload": record.payload,
        "state": record.state.value,
        "partition_key": record.partition_key,
        "priority": record.priority,
        "attempts": record.attempts,
        "max_attempts": record.max_attempts,
        "lease_owner": record.lease_owner,
        "lease_expires_at": record.lease_expires_at,
        "created_at": record.created_at,
        "completed_at": record.completed_at,
        "last_error": record.last_error,
    }


def _create_mock_transport_handler(
    backend: InMemoryTaskQueueAdapter,
) -> Any:
    """Create a mock HTTP transport handler delegating to InMemoryTaskQueueAdapter."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method

        if method == "POST" and path == "/api/v1/jobs":
            body = json.loads(request.content)
            record = backend.enqueue(
                task_name=body["task_name"],
                payload=body["payload"],
                partition_key=body.get("partition_key"),
                priority=int(body.get("priority", 0)),
                max_attempts=int(body.get("max_attempts", 3)),
            )
            return httpx.Response(200, json=_record_to_dict(record))

        if method == "POST" and path == "/api/v1/jobs/lease":
            body = json.loads(request.content)
            record = backend.lease_next(
                worker_id=body["worker_id"],
                task_names=body.get("task_names"),
                lease_duration_seconds=float(body.get("lease_duration_seconds", 30.0)),
            )
            if record is None:
                return httpx.Response(204)
            return httpx.Response(200, json=_record_to_dict(record))

        if (
            method == "POST"
            and path.startswith("/api/v1/jobs/")
            and path.endswith("/complete")
        ):
            task_id = path.split("/")[4]
            body = json.loads(request.content) if request.content else {}
            backend.complete(task_id, worker_id=body.get("worker_id"))
            return httpx.Response(200, json={"status": "completed"})

        if (
            method == "POST"
            and path.startswith("/api/v1/jobs/")
            and path.endswith("/fail")
        ):
            task_id = path.split("/")[4]
            body = json.loads(request.content) if request.content else {}
            backend.fail(
                task_id,
                error=body.get("error", "err"),
                worker_id=body.get("worker_id"),
            )
            return httpx.Response(200, json={"status": "failed"})

        if (
            method == "POST"
            and path.startswith("/api/v1/jobs/")
            and path.endswith("/renew")
        ):
            task_id = path.split("/")[4]
            body = json.loads(request.content) if request.content else {}
            renewed = backend.renew_lease(
                task_id,
                worker_id=body.get("worker_id", ""),
                lease_duration_seconds=float(body.get("lease_duration_seconds", 30.0)),
            )
            return httpx.Response(200 if renewed else 404, json={"renewed": renewed})

        return httpx.Response(404)

    return handler


def test_hexaqueue_sync_lifecycle_and_priority_leasing() -> None:
    """Verify synchronous enqueue, priority leasing, complete, and fail."""
    backend = InMemoryTaskQueueAdapter()
    handler = _create_mock_transport_handler(backend)

    mock_client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://test-hexaqueue:8000",
    )

    adapter = HexaqueueTaskQueueAdapter(
        cluster_url="http://test-hexaqueue:8000",
        token="test-secret-token",  # pragma: allowlist secret
        client=mock_client,
    )

    # 1. Enqueue two tasks with different priorities
    t_low = adapter.enqueue("sync_task", {"step": 1}, priority=1, max_attempts=1)
    assert t_low.state == TaskState.PENDING
    assert t_low.priority == 1

    t_high = adapter.enqueue("sync_task", {"step": 2}, priority=10)
    assert t_high.priority == 10

    # 2. Priority leasing: highest priority leased first
    leased_1 = adapter.lease_next("worker-sync-1", task_names=["sync_task"])
    assert leased_1 is not None
    assert leased_1.id == t_high.id
    assert leased_1.lease_owner == "worker-sync-1"

    # 3. Renew lease
    renewed = adapter.renew_lease(leased_1.id, "worker-sync-1", 60.0)
    assert renewed is True

    # Renew by incorrect worker fails
    renew_failed = adapter.renew_lease(leased_1.id, "wrong-worker", 60.0)
    assert renew_failed is False

    # 4. Complete task
    adapter.complete(leased_1.id, worker_id="worker-sync-1")
    assert backend._tasks[leased_1.id].state == TaskState.COMPLETED

    # 5. Lease next: gets lower priority task
    leased_2 = adapter.lease_next("worker-sync-2")
    assert leased_2 is not None
    assert leased_2.id == t_low.id

    # 6. Fail task
    adapter.fail(leased_2.id, error="Transient crash", worker_id="worker-sync-2")
    assert backend._tasks[leased_2.id].attempts == 1

    # 7. No more tasks available
    leased_empty = adapter.lease_next("worker-sync-3")
    assert leased_empty is None

    adapter.close()


@pytest.mark.anyio
async def test_hexaqueue_async_lifecycle_and_operations() -> None:
    """Verify asynchronous enqueue, leasing, renewal, and completion."""
    backend = InMemoryTaskQueueAdapter()
    handler = _create_mock_transport_handler(backend)

    mock_async_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://test-hexaqueue:8000",
    )

    adapter = HexaqueueTaskQueueAdapter(
        cluster_url="http://test-hexaqueue:8000",
        async_client=mock_async_client,
    )

    # 1. Enqueue async
    task = await adapter.enqueue_async(
        "async_job",
        {"data": "payload_val"},
        priority=5,
    )
    assert task.task_name == "async_job"
    assert task.priority == 5

    # 2. Lease async
    leased = await adapter.lease_next_async(
        "worker-async-1", lease_duration_seconds=45.0
    )
    assert leased is not None
    assert leased.id == task.id
    assert leased.lease_owner == "worker-async-1"

    # 3. Renew lease async
    renew_ok = await adapter.renew_lease_async(leased.id, "worker-async-1")
    assert renew_ok is True

    # 4. Complete async
    await adapter.complete_async(leased.id, worker_id="worker-async-1")
    assert backend._tasks[leased.id].state == TaskState.COMPLETED

    # 5. Empty lease returns None
    leased_none = await adapter.lease_next_async("worker-async-2")
    assert leased_none is None

    # 6. Fail async on another task
    task2 = await adapter.enqueue_async("fail_job", {}, max_attempts=1)
    assert task2.task_name == "fail_job"
    leased2 = await adapter.lease_next_async("worker-async-3")
    assert leased2 is not None

    await adapter.fail_async(
        leased2.id, error="Fatal exception", worker_id="worker-async-3"
    )
    assert backend._tasks[leased2.id].state == TaskState.DEAD_LETTERED

    await adapter.close_async()


def test_hexaqueue_parsing_and_error_handling() -> None:
    """Verify fallback parsing and HTTP error propagation."""
    adapter = HexaqueueTaskQueueAdapter(
        cluster_url="http://test-hexaqueue:8000",
        client=httpx.Client(),
    )
    rec = adapter._parse_task_record({"id": "custom", "state": "unknown_future_state"})
    assert rec.id == "custom"
    assert rec.state == TaskState.PENDING

    # Test error handling when cluster returns 500 Internal Server Error
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "server down"})

    err_client = httpx.Client(
        transport=httpx.MockTransport(error_handler),
        base_url="http://test-hexaqueue:8000",
    )
    err_adapter = HexaqueueTaskQueueAdapter(
        cluster_url="http://test-hexaqueue:8000",
        client=err_client,
    )

    with pytest.raises(httpx.HTTPStatusError):
        err_adapter.complete("task-1")

    with pytest.raises(httpx.HTTPStatusError):
        err_adapter.fail("task-1", error="boom")

    err_adapter.close()


@pytest.mark.anyio
async def test_hexaqueue_async_error_handling() -> None:
    """Verify async HTTP error propagation on completion/failure."""

    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "server down"})

    err_async_client = httpx.AsyncClient(
        transport=httpx.MockTransport(error_handler),
        base_url="http://test-hexaqueue:8000",
    )
    err_adapter = HexaqueueTaskQueueAdapter(
        cluster_url="http://test-hexaqueue:8000",
        async_client=err_async_client,
    )

    with pytest.raises(httpx.HTTPStatusError):
        await err_adapter.complete_async("task-1")

    with pytest.raises(httpx.HTTPStatusError):
        await err_adapter.fail_async("task-1", error="boom")

    await err_adapter.close_async()


def test_hexaqueue_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify MissingDependencyError is raised when httpx is missing."""
    monkeypatch.setitem(sys.modules, "httpx", None)

    with pytest.raises(MissingDependencyError, match="hexastack-events\\[hexaqueue\\]"):
        HexaqueueTaskQueueAdapter()
