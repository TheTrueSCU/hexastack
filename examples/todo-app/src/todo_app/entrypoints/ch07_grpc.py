"""Chapter 7 Entrypoint: High-Performance gRPC To-Do Service.

Run with:
    uv run python -m todo_app.entrypoints.ch07_grpc
"""

from __future__ import annotations

import grpc
from rodi import Container

from hexastack_core.infra.bootstrap import bootstrap
from hexastack_grpc.adapters.server import run_grpc_server

import todo_app.adapters.driving.grpc
import todo_app.infra.handlers
from todo_app.adapters.driven.sqlite import (
    SqliteTodoRepository,
    create_sqlite_session_factory,
)
from todo_app.ports.repositories import TodoRepositoryPort


def build_grpc_server(db_url: str = "sqlite:///todos_grpc.db") -> grpc.Server:
    """Build gRPC server daemon with SQLite repository adapter."""
    di = Container()
    session_factory = create_sqlite_session_factory(db_url=db_url)
    repo = SqliteTodoRepository(session_factory=session_factory)
    di.add_instance(repo, declared_class=TodoRepositoryPort)

    res = bootstrap(
        container=di,
        packages_to_scan=[
            todo_app.adapters.driving.grpc,
            todo_app.infra.handlers,
        ],
    )
    return res.container.resolve(grpc.Server)


if __name__ == "__main__":
    server = build_grpc_server()
    print("Starting gRPC server on 0.0.0.0:50051...")
    run_grpc_server(server, block=True)
