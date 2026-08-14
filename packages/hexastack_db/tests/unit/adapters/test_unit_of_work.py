import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from hexastack_core.domain.exceptions import UnitOfWorkError
from hexastack_db.adapters.unit_of_work import (
    AsyncSqlAlchemyUnitOfWork,
    SqlAlchemyUnitOfWork,
)
from hexastack_db.domain.exceptions import DatabaseError


class Base(DeclarativeBase):
    pass


class TaskRecord(Base):
    __tablename__ = "test_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str]


def test_sqlalchemy_unit_of_work_commit_and_rollback():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    uow = SqlAlchemyUnitOfWork(session_factory=session_factory)

    # Session property outside context raises DatabaseError
    with pytest.raises(DatabaseError, match="not active"):
        _ = uow.session

    # 1. Successful commit via context manager
    with uow:
        uow.session.add(TaskRecord(title="Task 1"))

    with session_factory() as session:
        tasks = session.execute(select(TaskRecord)).scalars().all()
        assert len(tasks) == 1
        assert tasks[0].title == "Task 1"

    # 2. Explicit commit and rollback
    with uow:
        uow.session.add(TaskRecord(title="Task 2"))
        uow.commit()

    with uow:
        uow.session.add(TaskRecord(title="Task 3 (rolled back)"))
        uow.rollback()

    with session_factory() as session:
        titles = [t.title for t in session.execute(select(TaskRecord)).scalars().all()]
        assert "Task 2" in titles
        assert "Task 3 (rolled back)" not in titles

    # 3. Rollback on exception
    try:
        with uow:
            uow.session.add(TaskRecord(title="Task 4 (fail)"))
            raise ValueError("Forced error")
    except ValueError:
        pass

    with session_factory() as session:
        titles = [t.title for t in session.execute(select(TaskRecord)).scalars().all()]
        assert "Task 4 (fail)" not in titles

    # 4. Reraise wraps in UnitOfWorkError
    uow_reraise = SqlAlchemyUnitOfWork(session_factory=session_factory, reraise=True)
    with pytest.raises(UnitOfWorkError), uow_reraise:
        raise ValueError("Wrapped error")


@pytest.mark.anyio
async def test_async_sqlalchemy_unit_of_work():
    async_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_factory = async_sessionmaker(bind=async_engine)
    async_uow = AsyncSqlAlchemyUnitOfWork(session_factory=async_factory)

    # Session outside context
    with pytest.raises(DatabaseError, match="not active"):
        _ = async_uow.session

    # 1. Successful commit
    async with async_uow:
        async_uow.session.add(TaskRecord(title="Async Task 1"))

    async with async_factory() as session:
        tasks = (await session.execute(select(TaskRecord))).scalars().all()
        assert len(tasks) == 1
        assert tasks[0].title == "Async Task 1"

    # 2. Explicit commit and rollback
    async with async_uow:
        async_uow.session.add(TaskRecord(title="Async Task 2"))
        await async_uow.commit()

    async with async_uow:
        async_uow.session.add(TaskRecord(title="Async Task 3 (rolled back)"))
        await async_uow.rollback()

    async with async_factory() as session:
        titles = [
            t.title for t in (await session.execute(select(TaskRecord))).scalars().all()
        ]
        assert "Async Task 2" in titles
        assert "Async Task 3 (rolled back)" not in titles

    # 3. Rollback on exception
    try:
        async with async_uow:
            async_uow.session.add(TaskRecord(title="Async Task 4 (fail)"))
            raise ValueError("Async forced error")
    except ValueError:
        pass

    async with async_factory() as session:
        titles = [
            t.title for t in (await session.execute(select(TaskRecord))).scalars().all()
        ]
        assert "Async Task 4 (fail)" not in titles

    # 4. Reraise wraps in UnitOfWorkError
    uow_async_reraise = AsyncSqlAlchemyUnitOfWork(
        session_factory=async_factory, reraise=True
    )
    with pytest.raises(UnitOfWorkError):
        async with uow_async_reraise:
            raise ValueError("Async wrapped error")
