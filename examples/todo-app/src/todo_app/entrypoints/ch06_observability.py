"""Chapter 6 Entrypoint: Fully Instrumented Production To-Do Service.

Run with:
    uv run python -m todo_app.entrypoints.ch06_observability
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from hexastack_core.adapters.logging import StandardLogger
from hexastack_core.adapters.notification import StdoutNotificationAdapter
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


def build_app(db_url: str = "sqlite:///todos_prod.db") -> FastAPI:
    """Build production-grade FastAPI app with logging and observability ports."""
    di = Container()
    session_factory = create_sqlite_session_factory(db_url=db_url)
    repo = SqliteTodoRepository(session_factory=session_factory)
    notifier = StdoutNotificationAdapter()
    logger = StandardLogger("todo_app.prod")

    di.add_instance(repo, declared_class=TodoRepositoryPort)
    di.add_instance(notifier, declared_class=NotificationPort)
    di.add_instance(logger, declared_class=LoggingPort)

    res = bootstrap(
        container=di,
        packages_to_scan=[
            todo_app.infra.handlers,
        ],
    )
    app = res.container.resolve(FastAPI)
    app.include_router(router)
    return app


app = build_app()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
