"""Chapter 5 Entrypoint: To-Do Service with MCP Server & AI Assistant.

Run with:
    uv run python -m todo_app.entrypoints.ch05_ai_mcp
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from hexastack_core.adapters.ai import InMemoryLlmProvider
from hexastack_core.adapters.feature_flags.in_memory import InMemoryFeatureFlagAdapter
from hexastack_core.adapters.notification import InMemoryNotificationAdapter
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.ai import LlmProviderPort
from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_core.ports.notification import NotificationPort
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from rodi import Container

import todo_app.adapters.driving.mcp
import todo_app.infra.handlers
from todo_app.adapters.driven.sqlite import (
    SqliteTodoRepository,
    create_sqlite_session_factory,
)
from todo_app.adapters.driving.http import router
from todo_app.domain.assistant import TodoAiAssistant
from todo_app.ports.repositories import TodoRepositoryPort


def build_app(
    db_url: str = "sqlite:///todos_ch05.db",
    enable_ai: bool = True,
) -> tuple[FastAPI, TodoAiAssistant]:
    """Build application kernel with SQLite persistence, Feature Flags, MCP tools, and AI Assistant."""
    di = Container()
    session_factory = create_sqlite_session_factory(db_url=db_url)
    repo = SqliteTodoRepository(session_factory=session_factory)
    notifier = InMemoryNotificationAdapter()
    flags = InMemoryFeatureFlagAdapter(flags={"experimental_ai_assistant": enable_ai})
    llm = InMemoryLlmProvider()

    di.add_instance(repo, declared_class=TodoRepositoryPort)
    di.add_instance(notifier, declared_class=NotificationPort)
    di.add_instance(flags, declared_class=FeatureFlagPort)
    di.add_instance(llm, declared_class=LlmProviderPort)

    res = bootstrap(
        container=di,
        packages_to_scan=[
            todo_app.infra.handlers,
        ],
    )
    pipeline = res.container.resolve(ExecutionPipeline)
    assistant = TodoAiAssistant(llm=llm, pipeline=pipeline)
    app = res.container.resolve(FastAPI)
    app.include_router(router)
    return app, assistant


app, _ = build_app()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
