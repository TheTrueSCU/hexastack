"""Chapter 2 Entrypoint: SQLite Persistent To-Do Service.

Run with:
    uv run python -m todo_app.entrypoints.ch02_sqlite
"""

import uvicorn
from fastapi import FastAPI
from hexastack_core.adapters.notification import InMemoryNotificationAdapter
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.notification import NotificationPort
from rodi import Container

import todo_app.infra.handlers
from todo_app.adapters.driven.sqlite import (
    SqliteTodoRepository,
    create_sqlite_session_factory,
)
from todo_app.adapters.driving.http import router
from todo_app.ports.repositories import TodoRepositoryPort


def build_app(db_url: str = "sqlite:///todos_ch02.db") -> FastAPI:
    """Build FastAPI app with SQLite repository adapter."""
    di = Container()
    session_factory = create_sqlite_session_factory(db_url=db_url)
    repo = SqliteTodoRepository(session_factory=session_factory)
    notifier = InMemoryNotificationAdapter()
    di.add_instance(repo, declared_class=TodoRepositoryPort)
    di.add_instance(notifier, declared_class=NotificationPort)

    res = bootstrap(
        container=di,
        packages_to_scan=[
            todo_app.infra.handlers,
        ],
    )
    app = res.container.resolve(FastAPI)
    app.include_router(router)
    return app


if __name__ == "__main__":
    app = build_app()
    uvicorn.run(app, host="127.0.0.1", port=8000)
