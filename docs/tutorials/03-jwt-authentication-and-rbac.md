# Tutorial 3: JWT Authentication & Role-Based Access Control (RBAC)

In this chapter, you will secure the To-Do microservice by attaching **JWT token extraction** and **Role-Based Access Control (RBAC)** to your CQRS commands and queries using `hexastack-auth`.

---

## 1. Domain User Roles & Permissions

Define permission policies in `src/todo_app/domain/models.py`:

```python
# src/todo_app/domain/models.py
from enum import StrEnum

class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"
```

---

## 2. Securing CQRS Commands with Auth Decorators

Decorate CQRS commands with required permissions using `hexastack_auth.infra.decorators`:

```python
# src/todo_app/domain/commands.py
from hexastack_auth.infra.decorators import require_role
from hexastack_core.domain import Command

# Anyone with role 'user' or 'admin' can create tasks
@require_role("user", "admin")
class CreateTodoCommand(Command):
    title: str
    description: str = ""

# Only 'admin' role can delete tasks
@require_role("admin")
class DeleteTodoCommand(Command):
    todo_id: str
```

---

## 3. Ambient UserContext in CQRS Execution Pipeline

When a request arrives at the FastAPI endpoint or CLI, `hexastack-auth` extracts the JWT bearer token, validates the claims, and sets the ambient `UserContext`:

```python
# Automatic context injection inside handlers
from hexastack_core.utils.context import get_user_context

def handle_create_todo(cmd: CreateTodoCommand, repo: TodoRepositoryPort) -> TodoItemDTO:
    user = get_user_context()
    # Associate task with current authenticated user
    user_id = user.user_id if user else "anonymous"
    ...
```

---

## 4. Testing Protected Endpoints

```python
# tests/unit/test_auth_pipeline.py
import pytest
from hexastack_auth.domain.exceptions import UnauthorizedError
from hexastack_core.utils.context import UserContext, set_user_context

def test_delete_todo_requires_admin(todo_repo):
    # Set standard user context
    set_user_context(UserContext(user_id="user1", roles=["user"]))

    del_cmd = DeleteTodoCommand(todo_id="item-123")
    with pytest.raises(UnauthorizedError):
        pipeline.execute(del_cmd)  # Blocked by AuthMiddleware
```
