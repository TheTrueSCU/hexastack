import pytest
from hexastack_core.domain.exceptions import UnitOfWorkError
from hexastack_db.adapters.unit_of_work import (
    AsyncSqlAlchemyUnitOfWork,
    SqlAlchemyUnitOfWork,
)
from hexastack_db.domain.exceptions import DatabaseError
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


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
    with pytest.raises(DatabaseError):
        _ = uow.session

    # 1. Successful commit via context manager
    with uow:
        uow.session.add(TaskRecord(title="Task 1"))

    with session_factory() as session:
        tasks = session.execute(select(TaskRecord)).scalars().all()
        assert len(tasks) == 1
        assert tasks[0].title == "Task 1"

    # 2. Rollback on exception
    try:
        with uow:
            uow.session.add(TaskRecord(title="Task 2 (fail)"))
            raise ValueError("Forced error")
    except ValueError:
        pass

    with session_factory() as session:
        tasks = session.execute(select(TaskRecord)).scalars().all()
        assert len(tasks) == 1

    # 3. Reraise wraps in UnitOfWorkError
    uow_reraise = SqlAlchemyUnitOfWork(session_factory=session_factory, reraise=True)
    with pytest.raises(UnitOfWorkError), uow_reraise:
        uow_reraise.session.add(TaskRecord(title="Task 3"))
        raise RuntimeError("Fatal error")

    engine.dispose()


@pytest.mark.anyio
async def test_async_sqlalchemy_unit_of_work():
    async_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_factory = async_sessionmaker(bind=async_engine)
    uow = AsyncSqlAlchemyUnitOfWork(session_factory=async_factory)

    # Session property outside context raises DatabaseError
    with pytest.raises(DatabaseError):
        _ = uow.session

    # 1. Successful async commit
    async with uow:
        uow.session.add(TaskRecord(title="Async Task 1"))

    async with async_factory() as session:
        res = await session.execute(select(TaskRecord))
        tasks = res.scalars().all()
        assert len(tasks) == 1
        assert tasks[0].title == "Async Task 1"

    # 2. Rollback on async exception
    try:
        async with uow:
            uow.session.add(TaskRecord(title="Async Task 2 (fail)"))
            raise ValueError("Async forced error")
    except ValueError:
        pass

    async with async_factory() as session:
        res = await session.execute(select(TaskRecord))
        tasks = res.scalars().all()
        assert len(tasks) == 1

    await async_engine.dispose()
