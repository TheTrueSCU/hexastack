from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from hexastack_core.domain.exceptions import UnitOfWorkError
from hexastack_core.testing.flags import require_extra
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


@require_extra("aiosqlite")
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

    # 2. Explicit commit and rollback (including commit_async / rollback_async aliases)
    async with async_uow:
        async_uow.session.add(TaskRecord(title="Async Task 2"))
        await async_uow.commit_async()

    async with async_uow:
        async_uow.session.add(TaskRecord(title="Async Task 3 (rolled back)"))
        await async_uow.rollback_async()

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
    try:
        async with uow_async_reraise:
            raise ValueError("Async wrapped error")
    except UnitOfWorkError:
        pass

    # 5. Commit failure in AsyncUnitOfWork raises UnitOfWorkError on exit
    failing_mock_session = MagicMock()

    async def mock_fail_commit():
        raise OperationalError("stmt", {}, Exception("mock error"))

    failing_mock_session.commit = mock_fail_commit

    async def mock_noop_rollback():
        pass

    failing_mock_session.rollback = mock_noop_rollback

    async def mock_noop_close():
        pass

    failing_mock_session.close = mock_noop_close

    failing_async_uow = AsyncSqlAlchemyUnitOfWork(
        session_factory=lambda: failing_mock_session
    )
    with pytest.raises(UnitOfWorkError):
        async with failing_async_uow:
            pass

    # 6. Session reset to None on exit and inactive commit/rollback no-op
    assert async_uow._session is None
    await async_uow.commit()
    await async_uow.commit_async()
    await async_uow.rollback()
    await async_uow.rollback_async()
    with pytest.raises(
        DatabaseError,
        match="AsyncUnitOfWork session is not active. Use within 'async with uow:' context.",
    ):
        _ = async_uow.session

    # 7. Explicit commit failure raises UnitOfWorkError and suppresses rollback errors
    error_mock_session = MagicMock()
    error_mock_session.commit = mock_fail_commit

    async def mock_fail_rollback():
        raise OperationalError("stmt", {}, Exception("rollback error"))

    error_mock_session.rollback = mock_fail_rollback
    error_mock_session.close = mock_noop_close

    explicit_fail_uow = AsyncSqlAlchemyUnitOfWork(
        session_factory=lambda: error_mock_session
    )
    await explicit_fail_uow.__aenter__()
    with pytest.raises(UnitOfWorkError):
        await explicit_fail_uow.commit()
    # Suppress rollback error
    await explicit_fail_uow.rollback()
    await explicit_fail_uow.__aexit__(ValueError, ValueError("test error"), None)


def test_sqlalchemy_unit_of_work_commit_and_rollback():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    uow = SqlAlchemyUnitOfWork(session_factory=session_factory)

    # Session property outside context raises DatabaseError with exact message
    with pytest.raises(
        DatabaseError,
        match="UnitOfWork session is not active. Use within 'with uow:' context.",
    ):
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

    # 5. Commit failure in sync UnitOfWork raises UnitOfWorkError on exit
    failing_mock_session = MagicMock()
    failing_mock_session.commit.side_effect = OperationalError(
        "stmt", {}, Exception("mock error")
    )
    failing_uow = SqlAlchemyUnitOfWork(session_factory=lambda: failing_mock_session)
    with pytest.raises(UnitOfWorkError), failing_uow:
        pass

    # 6. Session reset to None on exit and inactive commit/rollback no-op
    assert uow._session is None
    uow.commit()
    uow.rollback()
    with pytest.raises(
        DatabaseError,
        match="UnitOfWork session is not active. Use within 'with uow:' context.",
    ):
        _ = uow.session

    # 7. Explicit commit failure raises UnitOfWorkError and suppresses rollback errors
    error_mock_session = MagicMock()
    error_mock_session.commit.side_effect = OperationalError(
        "stmt", {}, Exception("mock error")
    )
    error_mock_session.rollback.side_effect = OperationalError(
        "stmt", {}, Exception("rollback error")
    )
    explicit_fail_sync_uow = SqlAlchemyUnitOfWork(
        session_factory=lambda: error_mock_session
    )
    explicit_fail_sync_uow.__enter__()
    with pytest.raises(UnitOfWorkError):
        explicit_fail_sync_uow.commit()
    # Suppress rollback error
    explicit_fail_sync_uow.rollback()
    explicit_fail_sync_uow.__exit__(ValueError, ValueError("test error"), None)
