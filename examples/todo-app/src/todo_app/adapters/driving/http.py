"""FastAPI HTTP driving adapters exposing CQRS commands and queries."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from hexastack_core.utils.context import UserContext, set_user_context
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_fastapi.adapters.dependencies import get_pipeline
from hexastack_fastapi.adapters.routing import CqrsRouter

from todo_app.domain.commands import (
    CompleteTodoCommand,
    CreateTodoCommand,
    DeleteTodoCommand,
    GetTodoQuery,
    ListTodosQuery,
    TodoItemDTO,
)

router = CqrsRouter(tags=["todos"])


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> UserContext:
    """Extract authenticated user context from Bearer token or fallback to demo anonymous."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        # Simulated/demo token parser: "user:bob" -> UserContext(user_id="bob", roles=["user"])
        # or "admin:superadmin" -> UserContext(user_id="superadmin", roles=["admin"])
        if ":" in token:
            role, user_id = token.split(":", 1)
            if role == "admin":
                # Verify caller identity is authorized for admin privileges
                if user_id != "superadmin":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid admin credentials: caller cannot claim admin role.",
                    )
                roles = ["admin"]
            elif role == "user":
                roles = ["user"]
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Unsupported identity role: '{role}'",
                )
            ctx = UserContext(user_id=user_id, roles=roles)
            set_user_context(ctx)
            return ctx
        ctx = UserContext(user_id=token, roles=["user"])
        set_user_context(ctx)
        return ctx

    # Default ambient user for unauthenticated requests
    ctx = UserContext(user_id="anonymous", roles=[])
    set_user_context(ctx)
    return ctx


@router.post("/todos", status_code=201, summary="Create a new To-Do task")
def create_todo(
    cmd: CreateTodoCommand,
    pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    user: Annotated[UserContext, Depends(get_current_user)],
) -> TodoItemDTO:
    # Non-admin users cannot spoof owner_id for another user; bind to authenticated user
    effective_owner = user.user_id
    if "admin" in user.roles and cmd.owner_id is not None:
        effective_owner = cmd.owner_id
    cmd = CreateTodoCommand(
        title=cmd.title,
        owner_id=effective_owner,
        description=cmd.description,
        priority=cmd.priority,
    )
    return pipeline.execute(cmd)


@router.get("/todos", summary="List all To-Do tasks")
def list_todos(
    pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    user: Annotated[UserContext, Depends(get_current_user)],
    completed_only: bool | None = None,
) -> list[TodoItemDTO]:
    # Regular users only see their own tasks; admins see all
    owner_filter = None if "admin" in user.roles else user.user_id
    query = ListTodosQuery(owner_id=owner_filter, completed_only=completed_only)
    return pipeline.execute(query)


@router.get("/todos/{todo_id}", summary="Get single To-Do task details")
def get_todo(
    todo_id: str,
    pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    user: Annotated[UserContext, Depends(get_current_user)],
) -> TodoItemDTO:
    query = GetTodoQuery(todo_id=todo_id)
    dto: TodoItemDTO = pipeline.execute(query)
    # Check read permissions
    if "admin" not in user.roles and dto.owner_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this To-Do item.",
        )
    return dto


@router.post("/todos/{todo_id}/complete", summary="Mark a To-Do task as completed")
def complete_todo(
    todo_id: str,
    pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    user: Annotated[UserContext, Depends(get_current_user)],
) -> TodoItemDTO:
    is_admin = "admin" in user.roles
    cmd = CompleteTodoCommand(
        todo_id=todo_id,
        requester_id=user.user_id,
        is_admin=is_admin,
    )
    return pipeline.execute(cmd)


@router.delete("/todos/{todo_id}", summary="Delete a To-Do task")
def delete_todo(
    todo_id: str,
    pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    user: Annotated[UserContext, Depends(get_current_user)],
) -> dict[str, bool]:
    is_admin = "admin" in user.roles
    cmd = DeleteTodoCommand(
        todo_id=todo_id,
        requester_id=user.user_id,
        is_admin=is_admin,
    )
    pipeline.execute(cmd)
    return {"deleted": True}


__all__ = [
    "get_current_user",
    "router",
]
