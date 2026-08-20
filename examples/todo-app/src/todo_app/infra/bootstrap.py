"""Hexastack bootstrapper and application kernel assembly."""

from fastapi import FastAPI
from rodi import Container

from hexastack_core.adapters.notification import InMemoryNotificationAdapter
from hexastack_core.infra.bootstrap import BootstrapResult, bootstrap
from hexastack_core.ports.notification import NotificationPort

import todo_app.adapters.driving.cli
import todo_app.adapters.driving.http
import todo_app.infra.handlers
from todo_app.adapters.driven.database import InMemoryTodoRepository
from todo_app.adapters.driving.http import router
from todo_app.ports.repositories import TodoRepositoryPort


def create_app() -> BootstrapResult:
    """Bootstrap full Hexastack microservice kernel."""
    di = Container()
    repo = InMemoryTodoRepository()
    notifier = InMemoryNotificationAdapter()
    di.add_instance(repo, declared_class=TodoRepositoryPort)
    di.add_instance(notifier, declared_class=NotificationPort)

    result = bootstrap(
        container=di,
        packages_to_scan=[
            todo_app.adapters.driving.cli,
            todo_app.infra.handlers,
        ],
    )
    app = result.container.resolve(FastAPI)
    app.include_router(router)
    return result
