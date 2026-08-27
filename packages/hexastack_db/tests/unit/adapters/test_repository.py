import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from hexastack_core.testing.flags import require_extra
from hexastack_db.adapters.repository import (
    AsyncSqlAlchemyRepository,
    SqlAlchemyRepository,
)
from hexastack_db.domain.exceptions import UniqueConstraintViolationError


class Base(DeclarativeBase):
    pass


class UserRecord(Base):
    __tablename__ = "test_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str]


@require_extra("aiosqlite")
@pytest.mark.anyio
async def test_async_sqlalchemy_repository():
    async_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_factory = async_sessionmaker(bind=async_engine)
    async with async_factory() as session:
        repo = AsyncSqlAlchemyRepository(session=session, model_cls=UserRecord)

        # 1. Add
        user1 = UserRecord(username="dave", email="dave@example.com")
        await repo.add(user1)
        assert user1.id is not None
        assert await repo.count() == 1

        # 2. Add many
        await repo.add_many(
            [
                UserRecord(username="eve", email="eve@example.com"),
                UserRecord(username="frank", email="frank@example.com"),
            ]
        )
        assert await repo.count() == 3

        # 3. Get
        fetched = await repo.get(user1.id)
        assert fetched is not None
        assert fetched.username == "dave"
        assert await repo.get(99999) is None

        # 4. List with offset and limit
        results = await repo.list(offset=1, limit=1)
        assert len(results) == 1

        # List with filter
        filtered = await repo.list(username="eve")
        assert len(filtered) == 1
        assert filtered[0].email == "eve@example.com"

        # Count with filter
        assert await repo.count(username="eve") == 1
        assert await repo.count(username="none") == 0

        # 5. Update
        user1.email = "dave_updated@example.com"
        await repo.update(user1)
        refetched = await repo.get(user1.id)
        assert refetched is not None
        assert refetched.email == "dave_updated@example.com"

        # 6. Aliases (add_async, get_by_id_async, remove_async)
        user_alias = UserRecord(username="grace", email="grace@example.com")
        await repo.add_async(user_alias)
        assert await repo.get_by_id_async(user_alias.id) is not None
        await repo.remove_async(user_alias.id)
        assert await repo.get_by_id_async(user_alias.id) is None

        # 7. Delete
        assert await repo.delete(user1.id) is True
        assert await repo.delete(999999) is False
        assert await repo.count() == 2

        # 8. Unique constraint errors
        # Note: repo.add("eve") will fail if "eve" is already in db
        await repo.add(UserRecord(username="unique_user", email="unique@example.com"))
        with pytest.raises(UniqueConstraintViolationError) as exc_info:
            await repo.add(UserRecord(username="unique_user", email="dup@example.com"))
        assert exc_info.value is not None
        assert (
            "UNIQUE constraint failed" in str(exc_info.value)
            or "unique" in str(exc_info.value).lower()
        )
        await session.rollback()

        # Re-add unique_user to test add_many duplicate against it
        await repo.add(UserRecord(username="unique_user", email="unique@example.com"))
        with pytest.raises(UniqueConstraintViolationError) as exc_info_many:
            await repo.add_many(
                [UserRecord(username="unique_user", email="dup2@example.com")]
            )
        assert (
            "UNIQUE constraint failed" in str(exc_info_many.value)
            or "unique" in str(exc_info_many.value).lower()
        )
        await session.rollback()

        # Test update causing duplicate username
        await repo.add(UserRecord(username="user_a", email="a@example.com"))
        user_b = UserRecord(username="user_b", email="b@example.com")
        await repo.add(user_b)

        user_b_conflict = UserRecord(
            id=user_b.id, username="user_a", email="b_updated@example.com"
        )
        with pytest.raises(UniqueConstraintViolationError):
            await repo.update(user_b_conflict)
        await session.rollback()


def test_sqlalchemy_repository_sync():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session: Session = session_factory()

    repo = SqlAlchemyRepository(session=session, model_cls=UserRecord)

    # 1. Add
    user1 = UserRecord(username="alice", email="alice@example.com")
    repo.add(user1)
    assert user1.id is not None
    assert repo.count() == 1

    # 2. Add many
    repo.add_many(
        [
            UserRecord(username="bob", email="bob@example.com"),
            UserRecord(username="charlie", email="charlie@example.com"),
        ]
    )
    assert repo.count() == 3

    # 3. Get
    fetched = repo.get(user1.id)
    assert fetched is not None
    assert fetched.username == "alice"
    assert repo.get(99999) is None

    # 4. List with offset and limit
    results = repo.list(offset=1, limit=1)
    assert len(results) == 1

    filtered = repo.list(username="bob")
    assert len(filtered) == 1
    assert filtered[0].email == "bob@example.com"

    # Count with filters
    assert repo.count(username="bob") == 1
    assert repo.count(username="missing") == 0

    # 5. Update
    user1.email = "alice_updated@example.com"
    merged = repo.update(user1)
    assert merged.email == "alice_updated@example.com"
    refetched = repo.get(user1.id)
    assert refetched is not None
    assert refetched.email == "alice_updated@example.com"

    # 6. Delete
    assert repo.delete(user1.id) is True
    assert repo.delete(999999) is False
    assert repo.count() == 2

    # 7. Unique constraint errors on add, add_many, and update
    repo.add(UserRecord(username="sync_unique", email="sync@example.com"))
    with pytest.raises(UniqueConstraintViolationError):
        repo.add(UserRecord(username="sync_unique", email="duplicate@example.com"))
    session.rollback()

    repo.add(UserRecord(username="sync_unique", email="sync@example.com"))
    with pytest.raises(UniqueConstraintViolationError):
        repo.add_many(
            [UserRecord(username="sync_unique", email="duplicate2@example.com")]
        )
    session.rollback()

    repo.add(UserRecord(username="user_1", email="1@example.com"))
    user_2 = UserRecord(username="user_2", email="2@example.com")
    repo.add(user_2)

    user_2_conflict = UserRecord(
        id=user_2.id, username="user_1", email="2_mod@example.com"
    )
    with pytest.raises(UniqueConstraintViolationError):
        repo.update(user_2_conflict)
    session.rollback()

    session.close()
    engine.dispose()


def test_sqlalchemy_repository_general_exception_handling():
    """Verify repository methods wrap unexpected sqlalchemy exceptions in DatabaseError."""
    from unittest.mock import MagicMock

    from hexastack_db.domain.exceptions import DatabaseError

    mock_session = MagicMock()
    mock_session.flush.side_effect = RuntimeError("DB driver crashed")
    mock_session.execute.side_effect = RuntimeError("DB execute crashed")

    repo = SqlAlchemyRepository(session=mock_session, model_cls=UserRecord)

    with pytest.raises(DatabaseError):
        repo.add(UserRecord(username="fail1", email="fail1@test.com"))

    with pytest.raises(DatabaseError):
        repo.add_many([UserRecord(username="fail2", email="fail2@test.com")])

    with pytest.raises(DatabaseError):
        repo.count()

    with pytest.raises(DatabaseError):
        repo.list()

    with pytest.raises(DatabaseError):
        repo.get(1)

    with pytest.raises(DatabaseError):
        repo.update(UserRecord(id=1, username="fail3", email="fail3@test.com"))

    with pytest.raises(DatabaseError):
        repo.delete(1)


@pytest.mark.anyio
async def test_async_sqlalchemy_repository_general_exception_handling():
    """Verify async repository methods wrap unexpected exceptions in DatabaseError."""
    from unittest.mock import AsyncMock, MagicMock

    from hexastack_db.domain.exceptions import DatabaseError

    mock_session = MagicMock()
    mock_session.flush = AsyncMock(side_effect=RuntimeError("Async DB driver crashed"))
    mock_session.execute = AsyncMock(side_effect=RuntimeError("Async execute crashed"))

    repo = AsyncSqlAlchemyRepository(session=mock_session, model_cls=UserRecord)

    with pytest.raises(DatabaseError):
        await repo.add(UserRecord(username="async_fail1", email="f1@test.com"))

    with pytest.raises(DatabaseError):
        await repo.add_many([UserRecord(username="async_fail2", email="f2@test.com")])

    with pytest.raises(DatabaseError):
        await repo.count()

    with pytest.raises(DatabaseError):
        await repo.list()

    with pytest.raises(DatabaseError):
        await repo.get(1)

    with pytest.raises(DatabaseError):
        await repo.update(UserRecord(id=1, username="async_fail3", email="f3@test.com"))

    with pytest.raises(DatabaseError):
        await repo.delete(1)
