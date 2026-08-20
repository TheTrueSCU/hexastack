"""Chapter 1 Entrypoint: In-Memory To-Do Service.

Run with:
    uv run python -m todo_app.entrypoints.ch01_in_memory
"""

import uvicorn
from fastapi import FastAPI

from hexastack_core.infra.bootstrap import bootstrap

import todo_app.adapters.driving.http
import todo_app.infra.handlers
from todo_app.adapters.driven.database import InMemoryTodoRepository
from todo_app.ports.repositories import TodoRepositoryPort


def build_app() -> FastAPI:
    """Build FastAPI app with in-memory persistence adapter."""
    repo = InMemoryTodoRepository()
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
