import pytest
from hexastack_db.adapters.repository import (
    AsyncSqlAlchemyRepository,
    SqlAlchemyRepository,
)
from hexastack_db.domain.exceptions import UniqueConstraintViolationError
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


class Base(DeclarativeBase):
    pass


class UserRecord(Base):
    __tablename__ = "test_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str]


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
    repo.update(user1)
    refetched = repo.get(user1.id)
    assert refetched is not None
    assert refetched.email == "alice_updated@example.com"

    # 6. Delete
    assert repo.delete(user1.id) is True
    assert repo.delete(999999) is False
    assert repo.count() == 2

    # 7. Unique constraint error
    with pytest.raises(UniqueConstraintViolationError):
        repo.add(UserRecord(username="bob", email="duplicate@example.com"))

    session.close()
    engine.dispose()


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

        # Count with filter
        assert await repo.count(username="eve") == 1
        assert await repo.count(username="none") == 0

        # 5. Update
        user1.email = "dave_updated@example.com"
        await repo.update(user1)
        refetched = await repo.get(user1.id)
        assert refetched is not None
        assert refetched.email == "dave_updated@example.com"

        # 6. Delete
        assert await repo.delete(user1.id) is True
        assert await repo.delete(999999) is False
        assert await repo.count() == 2

        # 7. Unique constraint error
        with pytest.raises(UniqueConstraintViolationError):
            await repo.add(UserRecord(username="eve", email="duplicate@example.com"))
