# Tutorial 2: SQLite Persistence & Alembic Migrations

In this chapter, you will transition the To-Do microservice from the ephemeral `InMemoryTodoRepository` to a persistent database adapter using **SQLAlchemy** and SQLite, without altering a single line of business logic in `domain/` or `ports/`.

---

## 1. The Power of Ports & Adapters

Because our application handlers in `src/todo_app/infra/handlers.py` only depend on the abstract `TodoRepositoryPort`, swapping the database adapter requires zero changes to your domain entities, CQRS commands, or HTTP routes:

```text
               ┌──────────────────────┐
               │  TodoRepositoryPort  │ (Interface in ports/)
               └──────────▲───────────┘
                          │
         ┌────────────────┴────────────────┐
         │                                 │
┌─────────────────────────┐     ┌─────────────────────────┐
│ InMemoryTodoRepository  │     │   SqliteTodoRepository  │ (Adapter in adapters/driven/)
└─────────────────────────┘     └─────────────────────────┘
```

---

## 2. SQLAlchemy ORM Model & Repository Adapter

Create `src/todo_app/adapters/driven/sqlite.py`:

```python
"""SQLAlchemy SQLite repository adapter for To-Do item persistence."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from todo_app.domain.models import Priority, TodoItem
from todo_app.ports.repositories import TodoRepositoryPort

Base = declarative_base()


class TodoItemModel(Base):
    """SQLAlchemy ORM table mapping for To-Do entities."""

    __tablename__ = "todos"

    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(String(1000), default="", nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    priority = Column(String(20), default="medium", nullable=False)


def create_sqlite_session_factory(db_url: str = "sqlite:///todos.db") -> sessionmaker:
    """Create configured SQLite SQLAlchemy session factory and create schema tables."""
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


class SqliteTodoRepository(TodoRepositoryPort):
    """SQLite-backed repository adapter using SQLAlchemy ORM sessions."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def save(self, item: TodoItem) -> None:
        with self._session_factory() as session:
            model = session.query(TodoItemModel).filter_by(id=item.id).first()
            priority_str = item.priority.value if hasattr(item.priority, "value") else str(item.priority)
            if model is None:
                model = TodoItemModel(
                    id=item.id,
                    title=item.title,
                    description=item.description or "",
                    completed=item.completed,
                    priority=priority_str,
                )
                session.add(model)
            else:
                model.title = item.title
                model.description = item.description or ""
                model.completed = item.completed
                model.priority = priority_str
            session.commit()

    def get_by_id(self, todo_id: str) -> TodoItem | None:
        with self._session_factory() as session:
            model = session.query(TodoItemModel).filter_by(id=todo_id).first()
            if model is None:
                return None
            return self._to_entity(model)

    def list_all(self, completed: bool | None = None) -> list[TodoItem]:
        with self._session_factory() as session:
            query = session.query(TodoItemModel)
            if completed is not None:
                query = query.filter_by(completed=completed)
            models = query.all()
            return [self._to_entity(m) for m in models]

    def delete(self, todo_id: str) -> bool:
        with self._session_factory() as session:
            model = session.query(TodoItemModel).filter_by(id=todo_id).first()
            if model is None:
                return False
            session.delete(model)
            session.commit()
            return True

    @staticmethod
    def _to_entity(model: TodoItemModel) -> TodoItem:
        return TodoItem(
            id=model.id,
            title=model.title,
            description=model.description,
            priority=Priority(model.priority),
            completed=model.completed,
        )
```

---

## 3. Dedicated Scoped Entrypoint (`ch02_sqlite.py`)

Create `src/todo_app/entrypoints/ch02_sqlite.py`:

```python
"""Chapter 2 Entrypoint: SQLite Persistent To-Do Service.

Run with:
    uv run python -m todo_app.entrypoints.ch02_sqlite
"""

import uvicorn
from fastapi import FastAPI

from hexastack_core.infra.bootstrap import bootstrap

import todo_app.adapters.driving.http
import todo_app.infra.handlers
from todo_app.adapters.driven.sqlite import (
    SqliteTodoRepository,
    create_sqlite_session_factory,
)
from todo_app.ports.repositories import TodoRepositoryPort


def build_app(db_url: str = "sqlite:///todos.db") -> FastAPI:
    """Build FastAPI app with SQLite repository adapter."""
    session_factory = create_sqlite_session_factory(db_url=db_url)
    repo = SqliteTodoRepository(session_factory=session_factory)
    res = bootstrap(
        packages_to_scan=[
            todo_app.adapters.driving.http,
            todo_app.infra.handlers,
        ]
    )
    res.container.add_instance(repo, declared_class=TodoRepositoryPort)
    return res.container.resolve(FastAPI)


app = build_app()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

---

## 4. Scaffolding & Terminal Experience

Watch the CLI setup for a persistent SQLite service:

<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; margin: 16px 0; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="../assets/demos/todo-ch02-cli-demo.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="../assets/demos/todo-ch02-cli-demo.vtt" default>
</video>

---

## 5. Verification: Persistent SQLite API

Watch the persistent REST endpoints executing live in Chromium:

<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; margin: 16px 0; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="../assets/demos/todo-ch02-browser-demo.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="../assets/demos/todo-ch02-browser-demo.vtt" default>
</video>

## 6. Next Steps: The Security Dilemma

We now have persistent storage across server restarts! But notice a critical vulnerability: **any caller can delete any To-Do item by ID**.

> *"What is stopping Bob from deleting Alice's tasks, or modifying tasks he doesn't own?"*

In Chapter 3, we introduce Hexastack's authentication kernel, JWT verification, and Role-Based Access Control (RBAC) to enforce task ownership and grant admin escalation privileges:

- **[Tutorial 3: Role-Based Access Control (RBAC) & JWT Auth](./03-jwt-authentication-and-rbac.md)**
- **[Tutorial 4: Event-Driven Architecture with Outbox & CloudEvents](./04-events-outbox-and-notifications.md)**
