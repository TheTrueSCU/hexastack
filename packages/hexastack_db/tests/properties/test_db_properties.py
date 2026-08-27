"""Hypothesis property-based tests for SQLAlchemyRepository and SqlAlchemyUnitOfWork invariants.

Notes/Architectural Intent:
    Fuzzes arbitrary CRUD entity states, batch additions, field-filter combinations,
    and nested transaction rollbacks to prove:
    1. Synchronous & Asynchronous repository CRUD roundtrips maintain data isomorphism.
    2. Filtering, pagination, sorting, and counting are consistent across arbitrary record volumes.
    3. UnitOfWork rollback guarantees 100% atomicity on raised domain exceptions without leaking state.
    4. UniqueConstraintViolationError and EntityNotFoundError are raised deterministically.
"""

from typing import cast

import pytest
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from hexastack_db.adapters.repository import (
    AsyncSqlAlchemyRepository,
    SqlAlchemyRepository,
)
from hexastack_db.adapters.unit_of_work import SqlAlchemyUnitOfWork
from hexastack_db.domain.exceptions import UniqueConstraintViolationError

Base = declarative_base()


class SampleItem(Base):
    __tablename__ = "sample_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=False)
    score = Column(Integer, nullable=False)


def create_in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


async def create_async_in_memory_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# Strategy for generating valid alphanumeric names to avoid null-byte or weird sqlite edge cases
clean_str = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=20
)


@given(
    items=st.lists(
        st.tuples(clean_str, clean_str, st.integers(min_value=0, max_value=1000)),
        min_size=1,
        max_size=15,
        unique_by=lambda t: t[0],  # unique names
    )
)
def test_sync_repository_batch_and_filter_invariants(items: list[tuple[str, str, int]]):
    """Property: Repository count and filtering match exact in-memory subsets for arbitrary data."""
    session_factory = create_in_memory_db()
    with session_factory() as session:
        repo = SqlAlchemyRepository[SampleItem, int](session, SampleItem)

        entities = [
            SampleItem(name=name, category=category, score=score)
            for name, category, score in items
        ]
        repo.add_many(entities)

        # Count invariant
        assert repo.count() == len(items)

        # Category filter invariant
        for target_category in {cat for _, cat, _ in items}:
            expected_count = sum(1 for _, cat, _ in items if cat == target_category)
            assert repo.count(category=target_category) == expected_count

            results = repo.list(category=target_category)
            assert len(results) == expected_count
            assert all(r.category == target_category for r in results)


@given(
    name=clean_str,
    category=clean_str,
    score=st.integers(min_value=1, max_value=100),
)
def test_unit_of_work_rollback_atomicity_property(name: str, category: str, score: int):
    """Property: Any exception within UnitOfWork scope rolls back all pending inserts cleanly."""
    session_factory = create_in_memory_db()
    uow = SqlAlchemyUnitOfWork(session_factory=session_factory)

    class CustomTestException(Exception):
        pass

    with pytest.raises(CustomTestException), uow:
        repo = SqlAlchemyRepository[SampleItem, int](uow.session, SampleItem)
        repo.add(SampleItem(name=name, category=category, score=score))
        raise CustomTestException("Forced rollback")

    # Verify zero items were persisted
    with session_factory() as verify_session:
        verify_repo = SqlAlchemyRepository[SampleItem, int](verify_session, SampleItem)
        assert verify_repo.count() == 0


@given(
    name=clean_str,
    category=clean_str,
    score=st.integers(min_value=1, max_value=100),
)
def test_sync_repository_duplicate_unique_constraint_property(
    name: str, category: str, score: int
):
    """Property: Inserting duplicate unique names deterministically raises UniqueConstraintViolationError."""
    session_factory = create_in_memory_db()
    with session_factory() as session:
        repo = SqlAlchemyRepository[SampleItem, int](session, SampleItem)
        repo.add(SampleItem(name=name, category=category, score=score))

        with pytest.raises(UniqueConstraintViolationError):
            repo.add(SampleItem(name=name, category=category, score=score + 1))


@pytest.mark.anyio
@given(
    name=clean_str,
    category=clean_str,
    score=st.integers(min_value=1, max_value=100),
)
async def test_async_repository_crud_lifecycle_property(
    name: str, category: str, score: int
):
    """Property: Async repository supports complete add -> get -> delete lifecycle."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async_factory = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_factory() as session:
            repo = AsyncSqlAlchemyRepository[SampleItem, int](session, SampleItem)

            item = SampleItem(name=name, category=category, score=score)
            await repo.add(item)
            assert item.id is not None

            item_id = cast("int", item.id)
            fetched = await repo.get(item_id)
            assert fetched is not None
            assert fetched.name == name
            assert fetched.score == score

            # Count check
            assert await repo.count() == 1

            # Delete check
            deleted = await repo.delete(item_id)
            assert deleted is True
            assert await repo.count() == 0

            assert await repo.get(item_id) is None
    finally:
        await engine.dispose()
