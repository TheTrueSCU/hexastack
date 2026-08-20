"""Unit and integration tests for Chapter 5 AI Assistant, MCP Tools, and Feature Flags."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from hexastack_mcp.infra.decorators import get_mcp_registry

from todo_app.domain.commands import (
    CompleteTodoCommand,
    CreateTodoCommand,
    DeleteTodoCommand,
    ListTodosQuery,
)
from todo_app.entrypoints.ch05_ai_mcp import build_app


@pytest.mark.ch05
def test_mcp_tools_registered_in_registry() -> None:
    """Verify MCP tools are discovered and registered in default McpServerRegistry."""
    registry = get_mcp_registry()
    tool_names = {t.name for t in registry.tools}

    assert "create_todo" in tool_names
    assert "list_todos" in tool_names
    assert "complete_todo" in tool_names
    assert "delete_todo" in tool_names


@pytest.mark.ch05
def test_mcp_tools_dispatch_cqrs_pipeline() -> None:
    """Verify CQRS commands & queries execute domain logic seamlessly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "ai_mcp_test.db"
        _, assistant = build_app(db_url=f"sqlite:///{db_path}")
        pipeline = assistant.pipeline

        # 1. Create Todo via Pipeline
        created = pipeline.execute(
            CreateTodoCommand(
                title="Train Llama 3 on Domain Docs",
                priority="high",
                owner_id="alice",
            )
        )
        assert created.title == "Train Llama 3 on Domain Docs"
        assert created.owner_id == "alice"

        # 2. List Todos via Pipeline
        todos = pipeline.execute(ListTodosQuery(owner_id="alice"))
        assert len(todos) == 1
        assert todos[0].id == created.id

        # 3. Complete Todo via Pipeline
        completed = pipeline.execute(CompleteTodoCommand(todo_id=created.id))
        assert completed.completed is True

        # 4. Delete Todo via Pipeline
        deleted = pipeline.execute(
            DeleteTodoCommand(todo_id=created.id, requester_id="alice")
        )
        assert deleted is True

        # Verify empty list
        remaining = pipeline.execute(ListTodosQuery(owner_id="alice"))
        assert len(remaining) == 0


@pytest.mark.ch05
def test_ai_assistant_morning_briefing() -> None:
    """Verify TodoAiAssistant queries pending tasks and generates morning executive briefing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "ai_briefing_test.db"
        _, assistant = build_app(db_url=f"sqlite:///{db_path}")
        pipeline = assistant.pipeline

        # Seed two pending tasks
        pipeline.execute(
            CreateTodoCommand(
                title="Ship Enterprise v1.0",
                priority="high",
                owner_id="alice",
            )
        )
        pipeline.execute(
            CreateTodoCommand(
                title="Update API Docs",
                priority="medium",
                owner_id="alice",
            )
        )

        # Generate briefing
        briefing = assistant.generate_morning_briefing(user_id="alice")
        assert isinstance(briefing, str)
        assert len(briefing) > 0
