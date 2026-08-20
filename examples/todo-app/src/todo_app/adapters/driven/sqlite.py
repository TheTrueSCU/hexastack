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
    owner_id = Column(String(100), default="alice", nullable=False)
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
        """Initialize repository with a SQLAlchemy sessionmaker.

        Args:
            session_factory: Configured SQLAlchemy sessionmaker instance.
        """
        self._session_factory = session_factory

    def save(self, item: TodoItem) -> None:
        """Persist or update To-Do entity in SQLite database."""
        with self._session_factory() as session:
            model = session.query(TodoItemModel).filter_by(id=item.id).first()
            priority_str = (
                item.priority.value
                if hasattr(item.priority, "value")
                else str(item.priority)
            )
            if model is None:
                model = TodoItemModel(
                    id=item.id,
                    owner_id=item.owner_id,
                    title=item.title,
                    description=item.description or "",
                    completed=item.completed,
                    priority=priority_str,
                )
                session.add(model)
            else:
                model.owner_id = item.owner_id
                model.title = item.title
                model.description = item.description or ""
                model.completed = item.completed
                model.priority = priority_str
            session.commit()

    def get_by_id(self, todo_id: str) -> TodoItem | None:
        """Fetch To-Do entity by identifier from SQLite database."""
        with self._session_factory() as session:
            model = session.query(TodoItemModel).filter_by(id=todo_id).first()
            if model is None:
                return None
            return self._to_entity(model)

    def list_all(self, completed: bool | None = None) -> list[TodoItem]:
        """List all To-Do entities optionally filtered by completion status."""
        with self._session_factory() as session:
            query = session.query(TodoItemModel)
            if completed is not None:
                query = query.filter_by(completed=completed)
            models = query.all()
            return [self._to_entity(m) for m in models]

    def delete(self, todo_id: str) -> bool:
        """Delete To-Do entity by identifier."""
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
            owner_id=getattr(model, "owner_id", "alice"),
            title=model.title,
            description=model.description,
            priority=Priority(model.priority),
            completed=model.completed,
        )


__all__ = [
    "SqliteTodoRepository",
    "TodoItemModel",
    "create_sqlite_session_factory",
]
