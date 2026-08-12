import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class HexastackBase(DeclarativeBase):
    """Shared SQLAlchemy declarative base for Hexastack applications.

    Notes/Architectural Intent:
        All user-defined ORM models should inherit from HexastackBase so that
        a single metadata object is shared across the application and alembic
        can discover all tables for autogeneration.
    """


class UuidPrimaryKeyMixin:
    """Mixin providing a UUID string primary key column named 'id'.

    Notes/Architectural Intent:
        Uses Python uuid4 generation at the application layer (not DB-generated)
        for portability across SQLite, PostgreSQL, and other backends.
        Stored as a 36-character VARCHAR for maximum compatibility.
    """

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        sort_order=-10,
    )


class TimestampMixin:
    """Mixin providing automatic 'created_at' and 'updated_at' timestamp columns.

    Notes/Architectural Intent:
        created_at is set once on INSERT using a Python-side default.
        updated_at is refreshed on every UPDATE via SQLAlchemy's onupdate hook.
        Both columns are timezone-aware (UTC) for global consistency.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        sort_order=100,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        sort_order=101,
    )


__all__ = [
    "HexastackBase",
    "TimestampMixin",
    "UuidPrimaryKeyMixin",
]
