"""Chapter 2 Entrypoint: SQLite Persistent To-Do Service.

Run with:
    uv run python -m todo_app.entrypoints.ch02_sqlite
"""

import uvicorn
from fastapi import FastAPI

from hexastack_core.infra.bootstrap import bootstrap

import todo_app.adapters.driving.http
import todo_app.infra.handlers
from todo_app.adapters.driven.sqlite import (
    SqliteTodoRepository,
    create_sqlite_session_factory,
)
from todo_app.ports.repositories import TodoRepositoryPort


def build_app(db_url: str = "sqlite:///todos.db") -> FastAPI:
    """Build FastAPI app with SQLite repository adapter."""
    session_factory = create_sqlite_session_factory(db_url=db_url)
    repo = SqliteTodoRepository(session_factory=session_factory)
    res = bootstrap(
        packages_to_scan=[
            todo_app.adapters.driving.http,
            todo_app.infra.handlers,
        ]
    )
    res.container.add_instance(repo, declared_class=TodoRepositoryPort)
    return res.container.resolve(FastAPI)


app = build_app()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
