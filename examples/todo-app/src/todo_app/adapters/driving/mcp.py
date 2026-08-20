"""Model Context Protocol (MCP) tool exposure for To-Do CQRS commands and queries."""

from __future__ import annotations

from typing import Any

from hexastack_mcp.infra.decorators import mcp_tool
from todo_app.domain.commands import (
    CompleteTodoCommand,
    CreateTodoCommand,
    DeleteTodoCommand,
    ListTodosQuery,
)

# Decorate pure CQRS Command & Query classes directly with @mcp_tool
mcp_create_todo = mcp_tool(
    name="create_todo",
    description="Create a new To-Do task with title, description, and priority level",
    kind="command",
)(CreateTodoCommand)

mcp_complete_todo = mcp_tool(
    name="complete_todo",
    description="Mark a To-Do task as completed by ID",
    kind="command",
)(CompleteTodoCommand)

mcp_delete_todo = mcp_tool(
    name="delete_todo",
    description="Delete a To-Do task by ID (as owner or admin)",
    kind="command",
)(DeleteTodoCommand)

mcp_list_todos = mcp_tool(
    name="list_todos",
    description="List all To-Do items with optional completion filter",
    kind="query",
)(ListTodosQuery)

__all__ = [
    "mcp_complete_todo",
    "mcp_create_todo",
    "mcp_delete_todo",
    "mcp_list_todos",
]
