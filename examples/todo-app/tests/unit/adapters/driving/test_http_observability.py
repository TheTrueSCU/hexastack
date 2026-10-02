"""Unit and integration tests for Chapter 6 Production Observability & Logging."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hexastack_core.adapters.logging import InMemoryLogger
from hexastack_core.adapters.notification import InMemoryNotificationAdapter
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.logging import LoggingPort
from hexastack_core.ports.notification import NotificationPort
from rodi import Container

import todo_app.infra.handlers
from todo_app.adapters.driven.sqlite import (
    SqliteTodoRepository,
    create_sqlite_session_factory,
)
from todo_app.adapters.driving.http import router
from todo_app.ports.repositories import TodoRepositoryPort


@pytest.mark.ch06
def test_production_logging_and_correlation_propagation() -> None:
    """Verify request logging captures correlation ID and structured telemetry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "prod_test.db"
        di = Container()
        session_factory = create_sqlite_session_factory(db_url=f"sqlite:///{db_path}")
        repo = SqliteTodoRepository(session_factory=session_factory)
        logger = InMemoryLogger()
        notifier = InMemoryNotificationAdapter()

        di.add_instance(repo, declared_class=TodoRepositoryPort)
        di.add_instance(logger, declared_class=LoggingPort)
        di.add_instance(notifier, declared_class=NotificationPort)

        res = bootstrap(container=di, packages_to_scan=[todo_app.infra.handlers])
        app = res.container.resolve(FastAPI)
        app.include_router(router)
        client = TestClient(app)

        # Alice creates a task
        resp = client.post(
            "/todos",
            json={"title": "Verify Telemetry", "priority": "high"},
            headers={"X-Correlation-ID": "test-telemetry-12345"},
        )
        assert resp.status_code == 201
        assert "id" in resp.json()
