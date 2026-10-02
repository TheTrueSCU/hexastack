"""Integration tests for SqlAlchemyRepository and UnitOfWork on real database backends."""

import pytest
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from hexastack_db.adapters.repository import SqlAlchemyRepository
from hexastack_db.adapters.unit_of_work import SqlAlchemyUnitOfWork
from hexastack_db.infra.config import HexastackDatabaseConfig
from hexastack_db.infra.engine import create_db_engine, create_session_factory


class Base(DeclarativeBase):
    pass


class AccountEntity(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(primary_key=True)
    owner: Mapped[str]
    balance: Mapped[float]


@pytest.mark.integration
def test_postgres_container_repository_and_uow(
    postgres_url: str, fake_user_id: str, fake_email: str
):
    """Verify SqlAlchemyRepository and UnitOfWork against an ephemeral integration database."""
    config = HexastackDatabaseConfig(url=postgres_url)
    engine = create_db_engine(config)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    uow = SqlAlchemyUnitOfWork(session_factory)

    # 1. Add record inside Unit of Work transactional block
    with uow:
        repo = SqlAlchemyRepository(session=uow.session, model_cls=AccountEntity)
        account = AccountEntity(id=fake_user_id, owner=fake_email, balance=1500.0)
        repo.add(account)
        uow.commit()

    # 2. Read back in a fresh session
    verify_session = session_factory()
    try:
        verify_repo = SqlAlchemyRepository(
            session=verify_session, model_cls=AccountEntity
        )
        saved = verify_repo.get(fake_user_id)
        assert saved is not None
        assert saved.owner == fake_email
        assert saved.balance == 1500.0
        assert verify_repo.count() == 1
    finally:
        verify_session.close()
        engine.dispose()
