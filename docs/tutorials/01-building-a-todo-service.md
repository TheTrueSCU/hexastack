# Tutorial 1: Building a To-Do Microservice with Hexastack

Welcome to the foundational tutorial for **Hexastack**!

In this guide, you will learn how to build a clean, production-grade To-Do microservice strictly following **Hexagonal Architecture (Ports & Adapters)** and **CQRS (Command-Query Responsibility Segregation)**.

By the end of this tutorial, you will have:
- A pure domain model with zero external framework dependencies.
- CQRS commands and queries decoupled from transport layers.
- Inverted storage ports and database adapters.
- Automatic multi-transport exposure (**FastAPI REST endpoints** and **Typer CLI** commands with zero duplicate logic).
- Live interactive inspection and debugging via **Hexastack DevTools**.
- Architectural guardrails enforced by **import-linter**.

---

## 1. Project Scaffolding (Zero to Hexagonal in Seconds)

Hexastack comes with an opinionated scaffolding engine that sets up a full project layout, tiered GitHub Actions CI, pre-commit hooks, and test runners out of the box.

The `hexastack new` command provides dedicated subcommands for each microservice archetype:
- `hexastack new web-api <name>`: Full REST API service with FastAPI, unit-of-work, and DevTools UI.
- `hexastack new grpc-service <name>`: High-performance gRPC binary microservice (Protobuf + Reflection).
- `hexastack new graphql-service <name>`: GraphQL data-graph gateway with Strawberry and GraphiQL IDE.
- `hexastack new event-driven <name>`: Event-streaming service with CloudEvents and Outbox pattern.
- `hexastack new mcp-agent <name>`: AI Model Context Protocol server and agent tool executor.
- `hexastack new minimal <name>`: Lightweight CLI or worker service (Core + CQRS + Logging).
- `hexastack init`: Interactive questionnaire wizard prompting for architecture, database, and transport options.

Run the following command in your terminal to scaffold our To-Do service:

```bash
# Using uv / uvx
uvx hexastack new web-api todo-app --description "Hexagonal To-Do Microservice" --db in-memory
```

<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; margin: 16px 0; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="../assets/demos/todo-ch01-cli-demo.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="../assets/demos/todo-ch01-cli-demo.vtt" default>
</video>

Let's navigate into the newly created service:

```bash
cd todo-app
```

### Generated Project Structure

```text
todo-app/
├── .github/
│   └── workflows/
│       └── ci.yml                 # Tiered CI: Fast check on push, fuzzing on PR
├── .importlinter                 # Hexagonal layer contracts
├── .pre-commit-config.yaml       # Ruff, ty, complexipy, and import-linter
├── pyproject.toml
├── src/
│   └── todo_app/
│       ├── domain/                # 1. Pure Python Domain (Models, CQRS Messages)
│       │   ├── __init__.py
│       │   ├── commands.py
│       │   └── models.py
│       ├── ports/                 # 2. Secondary Abstract Port Interfaces
│       │   ├── __init__.py
│       │   └── repositories.py
│       ├── adapters/              # 3. Primary & Secondary Adapters
│       │   ├── driving/           # Inbound (HTTP routes, CLI commands)
│       │   │   ├── cli.py
│       │   │   └── http.py
│       │   └── driven/            # Outbound (Database repositories)
│       │       └── database.py
│       └── infra/                 # 4. Kernel Assembly & Wiring
│           ├── bootstrap.py
│           ├── config.py
│           └── handlers.py
└── tests/
    ├── conftest.py
    ├── unit/
    └── hypothesis/
```

---

## 2. Core Domain: Entities & Invariants

In Hexagonal Architecture, your **Domain** is the heart of your software. It is 100% pure Python, completely unaware of web frameworks (FastAPI), databases (SQLAlchemy/SQLite), or CLI libraries.

Open `src/todo_app/domain/models.py` and define the To-Do entity, priority enum, and domain exceptions:

```python
# src/todo_app/domain/models.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TodoDomainError(Exception):
    """Base domain exception."""

    pass


class TodoNotFoundError(TodoDomainError):
    def __init__(self, todo_id: str) -> None:
        super().__init__(f"To-Do item '{todo_id}' not found.")
        self.todo_id = todo_id


class TodoAlreadyCompletedError(TodoDomainError):
    def __init__(self, todo_id: str) -> None:
        super().__init__(f"To-Do item '{todo_id}' is already completed.")
        self.todo_id = todo_id


@dataclass
class TodoItem:
    """Core domain entity representing a task."""

    title: str
    description: str = ""
    priority: Priority = Priority.MEDIUM
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    completed: bool = False

    def mark_completed(self) -> None:
        """Enforce domain transition rule."""
        if self.completed:
            raise TodoAlreadyCompletedError(self.id)
        self.completed = True
```

---

## 3. CQRS Contracts: Commands & Queries

Next, define the application's intent using **CQRS**. Commands represent state modifications; Queries represent data retrieval.

Open `src/todo_app/domain/commands.py`:

```python
# src/todo_app/domain/commands.py
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from hexastack_core.domain import Command, Query
from todo_app.domain.models import Priority


class CreateTodoCommand(Command):
    title: str = Field(..., min_length=1, description="Title of the task.")
    description: str = Field("", description="Optional task details.")
    priority: Priority = Field(Priority.MEDIUM, description="Task urgency level.")


class CompleteTodoCommand(Command):
    todo_id: str = Field(..., description="Unique ID of the task to complete.")


class DeleteTodoCommand(Command):
    todo_id: str = Field(..., description="Unique ID of the task to delete.")


class TodoItemDTO(BaseModel):
    id: str
    title: str
    description: str
    priority: Priority
    completed: bool


class ListTodosQuery(Query[list[TodoItemDTO]]):
    completed_only: Optional[bool] = Field(None, description="Filter by status.")


class GetTodoQuery(Query[TodoItemDTO]):
    todo_id: str = Field(..., description="Unique ID of the task.")
```

---

## 4. Secondary Ports: Abstract Persistence

The domain needs to persist entities, but it must not know about database details. We define an abstract **Port** in `src/todo_app/ports/repositories.py`:

```python
# src/todo_app/ports/repositories.py
from abc import ABC, abstractmethod
from typing import Optional
from todo_app.domain.models import TodoItem


class TodoRepositoryPort(ABC):
    """Abstract port for To-Do item persistence."""

    @abstractmethod
    def save(self, item: TodoItem) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, todo_id: str) -> Optional[TodoItem]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self, completed: Optional[bool] = None) -> list[TodoItem]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, todo_id: str) -> bool:
        raise NotImplementedError
```

---

## 5. Driven Adapters: Database Implementation

We implement the port in `src/todo_app/adapters/driven/database.py`. For local development and fast testing, we use an in-memory repository:

```python
# src/todo_app/adapters/driven/database.py
from typing import Optional
from todo_app.domain.models import TodoItem
from todo_app.ports.repositories import TodoRepositoryPort


class InMemoryTodoRepository(TodoRepositoryPort):
    def __init__(self) -> None:
        self._storage: dict[str, TodoItem] = {}

    def save(self, item: TodoItem) -> None:
        self._storage[item.id] = item

    def get_by_id(self, todo_id: str) -> Optional[TodoItem]:
        return self._storage.get(todo_id)

    def list_all(self, completed: Optional[bool] = None) -> list[TodoItem]:
        items = list(self._storage.values())
        if completed is not None:
            return [i for i in items if i.completed is completed]
        return items

    def delete(self, todo_id: str) -> bool:
        return self._storage.pop(todo_id, None) is not None
```

---

## 6. Application Logic: Handlers

In `src/todo_app/infra/handlers.py`, implement pure handler functions that accept the command/query and the injected repository port:

```python
# src/todo_app/infra/handlers.py
from todo_app.domain.commands import (
    CreateTodoCommand,
    CompleteTodoCommand,
    DeleteTodoCommand,
    ListTodosQuery,
    GetTodoQuery,
    TodoItemDTO,
)
from todo_app.domain.models import TodoItem, TodoNotFoundError
from todo_app.ports.repositories import TodoRepositoryPort


def _to_dto(item: TodoItem) -> TodoItemDTO:
    return TodoItemDTO(
        id=item.id,
        title=item.title,
        description=item.description,
        priority=item.priority,
        completed=item.completed,
    )


def handle_create_todo(cmd: CreateTodoCommand, repo: TodoRepositoryPort) -> TodoItemDTO:
    item = TodoItem(title=cmd.title, description=cmd.description, priority=cmd.priority)
    repo.save(item)
    return _to_dto(item)


def handle_complete_todo(
    cmd: CompleteTodoCommand, repo: TodoRepositoryPort
) -> TodoItemDTO:
    item = repo.get_by_id(cmd.todo_id)
    if item is None:
        raise TodoNotFoundError(cmd.todo_id)
    item.mark_completed()
    repo.save(item)
    return _to_dto(item)


def handle_delete_todo(cmd: DeleteTodoCommand, repo: TodoRepositoryPort) -> bool:
    deleted = repo.delete(cmd.todo_id)
    if not deleted:
        raise TodoNotFoundError(cmd.todo_id)
    return True


def handle_list_todos(
    query: ListTodosQuery, repo: TodoRepositoryPort
) -> list[TodoItemDTO]:
    return [_to_dto(i) for i in repo.list_all(completed=query.completed_only)]


def handle_get_todo(query: GetTodoQuery, repo: TodoRepositoryPort) -> TodoItemDTO:
    item = repo.get_by_id(query.todo_id)
    if item is None:
        raise TodoNotFoundError(query.todo_id)
    return _to_dto(item)
```

---

## 7. Driving Transports: Multi-Protocol Exposure

With Hexastack, exposing your CQRS commands to HTTP and CLI requires zero boilerplate:

### FastAPI REST Endpoints (`src/todo_app/adapters/driving/http.py`)

```python
# src/todo_app/adapters/driving/http.py
from hexastack_fastapi.infra.decorators import api_command, api_query
from todo_app.domain.commands import (
    CreateTodoCommand,
    CompleteTodoCommand,
    DeleteTodoCommand,
    ListTodosQuery,
    GetTodoQuery,
)

api_command("/todos", method="POST", status_code=201, summary="Create task")(
    CreateTodoCommand
)
api_command("/todos/{todo_id}/complete", method="POST", summary="Complete task")(
    CompleteTodoCommand
)
api_command("/todos/{todo_id}", method="DELETE", summary="Delete task")(
    DeleteTodoCommand
)
api_query("/todos", summary="List tasks")(ListTodosQuery)
api_query("/todos/{todo_id}", summary="Get task details")(GetTodoQuery)
```

### CLI Terminal Commands (`src/todo_app/adapters/driving/cli.py`)

```python
# src/todo_app/adapters/driving/cli.py
from hexastack_cli.infra.decorators import cli_command, cli_query
from todo_app.domain.commands import (
    CreateTodoCommand,
    CompleteTodoCommand,
    DeleteTodoCommand,
    ListTodosQuery,
)

cli_command("create", help="Create a new task.")(CreateTodoCommand)
cli_command("complete", help="Complete a task.")(CompleteTodoCommand)
cli_command("delete", help="Delete a task.")(DeleteTodoCommand)
cli_query("list", help="List all tasks.")(ListTodosQuery)
```

---

## 8. Assembly & Bootstrapping

Wire handlers and dependencies together in `src/todo_app/infra/bootstrap.py`:

```python
# src/todo_app/infra/bootstrap.py
from typing import Any
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_cqrs.infra.decorators import handle

import todo_app.adapters.driving.cli
import todo_app.adapters.driving.http
from todo_app.adapters.driven.database import InMemoryTodoRepository
from todo_app.domain.commands import (
    CreateTodoCommand,
    CompleteTodoCommand,
    DeleteTodoCommand,
    ListTodosQuery,
    GetTodoQuery,
)
from todo_app.infra.handlers import (
    handle_create_todo,
    handle_complete_todo,
    handle_delete_todo,
    handle_list_todos,
    handle_get_todo,
)
from todo_app.ports.repositories import TodoRepositoryPort

# Register CQRS Handlers
handle(CreateTodoCommand)(handle_create_todo)
handle(CompleteTodoCommand)(handle_complete_todo)
handle(DeleteTodoCommand)(handle_delete_todo)
handle(ListTodosQuery)(handle_list_todos)
handle(GetTodoQuery)(handle_get_todo)


def create_app() -> dict[str, Any]:
    result = bootstrap(
        packages_to_scan=[
            todo_app.adapters.driving.cli,
            todo_app.adapters.driving.http,
        ],
    )
    repo = InMemoryTodoRepository()
    result.container.add_instance(repo, declared_class=TodoRepositoryPort)
    return result
```

---

## 9. Verification: Tests & Architectural Linter

### Run All Unit & Property Tests

```bash
uv run pytest
```

Expected output:
```text
============================== 3 passed in 0.45s ===============================
```

### Inspect Architecture & Registered Routes

Ensure your CQRS commands and REST endpoints are correctly bound and discovered:

```bash
# 1. Inspect registered CQRS commands, queries, and handlers
uv run hexastack inspect registry

# 2. Introspect registered FastAPI REST routes and HTTP methods
uv run hexastack fastapi routes

# 3. Verify environment and installed Hexastack packages
uv run hexastack inspect info
```

### Interactive OpenAPI Testing & Swagger UI

Launch the dev server to explore the Swagger UI and interactive OpenAPI schema:

```bash
uv run hexastack serve --port 8000
```

Open your browser at `http://127.0.0.1:8000/docs` to test endpoints interactively with real-time JSON validation.

---

## 10. Next Steps & Advanced Modules

Congratulations! You now have a complete, fully tested hexagonal microservice.

Choose what to build next:
- **[Tutorial 2: Adding SQLite Persistence & Alembic Migrations](./02-sqlite-persistence-and-migrations.md)**
- **[Tutorial 3: Role-Based Access Control (RBAC) & JWT Auth](./03-jwt-authentication-and-rbac.md)**
- **[Tutorial 4: Event-Driven Architecture with Outbox & CloudEvents](./04-events-outbox-and-notifications.md)**
