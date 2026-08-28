"""CQRS command and query contracts for the To-Do service.

Notes/Architectural Intent:
    Defines immutable data transfer schemas for driving inbound requests (FastAPI, CLI).
"""

from __future__ import annotations

from hexastack_core.domain import Command, Query
from pydantic import BaseModel, Field

from todo_app.domain.models import Priority


class CreateTodoCommand(Command):
    """Command to create a new To-Do task."""

    title: str = Field(..., min_length=1, description="Title of the task.")
    owner_id: str = Field("alice", description="Owner identifier of the task.")
    description: str = Field("", description="Optional details or context.")
    priority: Priority = Field(Priority.MEDIUM, description="Task urgency level.")


class CompleteTodoCommand(Command):
    """Command to mark an existing To-Do task as finished."""

    todo_id: str = Field(..., description="Unique identifier of the task.")


class DeleteTodoCommand(Command):
    """Command to remove a task from the list."""

    todo_id: str = Field(..., description="Unique identifier of the task.")
    requester_id: str = Field(
        "alice", description="Caller identifier performing the deletion."
    )
    is_admin: bool = Field(
        False, description="Whether the caller has admin override privileges."
    )


class TodoItemDTO(BaseModel):
    """Read projection of a To-Do item."""

    id: str
    title: str
    owner_id: str
    description: str
    priority: Priority
    completed: bool


class ListTodosQuery(Query[list[TodoItemDTO]]):
    """Query to list To-Do items with optional completion filter."""

    owner_id: str | None = Field(None, description="Optional owner filter.")
    completed_only: bool | None = Field(
        None, description="Filter by completion status."
    )


class GetTodoQuery(Query[TodoItemDTO]):
    """Query to fetch a single To-Do item by ID."""

    todo_id: str = Field(..., description="Unique identifier of the task.")
