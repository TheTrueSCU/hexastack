# Tutorial 2: SQLite Persistence & Alembic Migrations

In this chapter, you will transition the To-Do microservice from the ephemeral `InMemoryTodoRepository` to a persistent database adapter using **SQLAlchemy Async Engine** and **Alembic migrations**, without altering a single line of business logic in `domain/` or `ports/`.

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
# src/todo_app/adapters/driven/sqlite.py
from typing import Optional
from sqlalchemy import Boolean, Column, Enum as SAEnum, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from todo_app.domain.models import Priority, TodoItem
from todo_app.ports.repositories import TodoRepositoryPort

Base = declarative_base()


class TodoORM(Base):
    """SQLAlchemy ORM table mapping for To-Do items."""

    __tablename__ = "todos"

    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(String(1000), default="")
    priority = Column(SAEnum(Priority), default=Priority.MEDIUM)
    completed = Column(Boolean, default=False)


class SqliteTodoRepository(TodoRepositoryPort):
    """Persistent SQLite database repository adapter."""

    def __init__(self, db_url: str = "sqlite:///todos.db") -> None:
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def save(self, item: TodoItem) -> None:
        with self.SessionLocal() as session:
            existing = session.query(TodoORM).filter(TodoORM.id == item.id).first()
            if existing:
                existing.title = item.title
                existing.description = item.description
                existing.priority = item.priority
                existing.completed = item.completed
            else:
                orm_item = TodoORM(
                    id=item.id,
                    title=item.title,
                    description=item.description,
                    priority=item.priority,
                    completed=item.completed,
                )
                session.add(orm_item)
            session.commit()

    def get_by_id(self, todo_id: str) -> Optional[TodoItem]:
        with self.SessionLocal() as session:
            row = session.query(TodoORM).filter(TodoORM.id == todo_id).first()
            if not row:
                return None
            return TodoItem(
                id=row.id,
                title=row.title,
                description=row.description,
                priority=row.priority,
                completed=row.completed,
            )

    def list_all(self, completed: Optional[bool] = None) -> list[TodoItem]:
        with self.SessionLocal() as session:
            query = session.query(TodoORM)
            if completed is not None:
                query = query.filter(TodoORM.completed == completed)
            return [
                TodoItem(
                    id=r.id,
                    title=r.title,
                    description=r.description,
                    priority=r.priority,
                    completed=r.completed,
                )
                for r in query.all()
            ]

    def delete(self, todo_id: str) -> bool:
        with self.SessionLocal() as session:
            row = session.query(TodoORM).filter(TodoORM.id == todo_id).first()
            if row:
                session.delete(row)
                session.commit()
                return True
            return False
```

---

## 3. Wiring the Database Adapter in Bootstrapper

Update `src/todo_app/infra/bootstrap.py`:

```python
# src/todo_app/infra/bootstrap.py
import os
from hexastack_core.infra.bootstrap import BootstrapResult, bootstrap
from todo_app.adapters.driven.sqlite import SqliteTodoRepository
from todo_app.ports.repositories import TodoRepositoryPort

def create_app() -> BootstrapResult:
    result = bootstrap(packages_to_scan=[...])

    # Switch repository from in-memory to SQLite
    db_url = os.environ.get("DATABASE_URL", "sqlite:///todos.db")
    repo = SqliteTodoRepository(db_url=db_url)
    result.container.add_instance(repo, declared_class=TodoRepositoryPort)
    return result
```

---

## 4. Managing Migrations with `hexastack db`

Hexastack CLI bundles turnkey Alembic migration workflows:

```bash
# 1. Initialize migration environment
hexastack db init

# 2. Generate migration revision
hexastack db revision "create todos table" --no-autogenerate

# 3. Apply migrations to database
hexastack db migrate
```
