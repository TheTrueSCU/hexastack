"""Chapter 1 Entrypoint: In-Memory To-Do Service.

Run with:
    uv run python -m todo_app.entrypoints.ch01_in_memory
"""

import uvicorn
from fastapi import FastAPI
from hexastack_core.adapters.notification import InMemoryNotificationAdapter
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.notification import NotificationPort
from rodi import Container

import todo_app.infra.handlers
from todo_app.adapters.driven.database import InMemoryTodoRepository
from todo_app.adapters.driving.http import router
from todo_app.ports.repositories import TodoRepositoryPort


def build_app() -> FastAPI:
    """Build FastAPI app with in-memory persistence adapter."""
    di = Container()
    repo = InMemoryTodoRepository()
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


app = build_app()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
