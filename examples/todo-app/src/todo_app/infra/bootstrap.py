"""Hexastack bootstrapper and application kernel assembly."""

from hexastack_core.infra.bootstrap import BootstrapResult, bootstrap
import todo_app.adapters.driving.cli
import todo_app.adapters.driving.http
import todo_app.infra.handlers
from todo_app.adapters.driven.database import InMemoryTodoRepository
from todo_app.ports.repositories import TodoRepositoryPort


def create_app() -> BootstrapResult:
    """Bootstrap full Hexastack microservice kernel."""
    repo = InMemoryTodoRepository()
    result = bootstrap(
        packages_to_scan=[
            todo_app.adapters.driving.cli,
            todo_app.adapters.driving.http,
            todo_app.infra.handlers,
        ],
    )
    result.container.add_instance(repo, declared_class=TodoRepositoryPort)
    return result
