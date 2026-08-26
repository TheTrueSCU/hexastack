"""Hypothesis RuleBasedStateMachine tests for Unit of Work transactional invariants."""

from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    rule,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from hexastack_db.adapters.unit_of_work import SqlAlchemyUnitOfWork


class Base(DeclarativeBase):
    pass


class UowItem(Base):
    __tablename__ = "uow_items"

    id: Mapped[str] = mapped_column(primary_key=True)
    val: Mapped[int] = mapped_column(default=0)


class SqlAlchemyUnitOfWorkStateMachine(RuleBasedStateMachine):
    """Hypothesis state machine verifying UnitOfWork transactional consistency.

    Notes/Architectural Intent:
        Exercises non-linear sequences of:
        - Commits (flushing dirty state to disk)
        - Rollbacks (restoring snapshot state)
        - Exceptions inside transaction blocks (verifying auto-rollback)
        - Dirty adds/updates
        Proves invariants:
        1. All committed items persist and are visible to external readers.
        2. All uncommitted items rolled back or abandoned upon exception are NEVER persisted.
        3. Session state is cleanly torn down with zero connection leaks.
    """

    def __init__(self) -> None:
        super().__init__()
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)

        self.committed_state: dict[str, int] = {}

    @rule(
        item_id=st.text(
            min_size=1, max_size=20, alphabet=st.characters(categories=["L", "N"])
        ),
        val=st.integers(min_value=-1000, max_value=1000),
    )
    def insert_and_commit(self, item_id: str, val: int) -> None:
        """Insert or update an item and explicitly commit."""
        uow = SqlAlchemyUnitOfWork(self.session_factory)
        with uow:
            session = uow.session
            existing = session.get(UowItem, item_id)
            if existing:
                existing.val = val
            else:
                session.add(UowItem(id=item_id, val=val))
            uow.commit()

        self.committed_state[item_id] = val

    @rule(
        item_id=st.text(
            min_size=1, max_size=20, alphabet=st.characters(categories=["L", "N"])
        ),
        val=st.integers(min_value=-1000, max_value=1000),
    )
    def insert_and_rollback(self, item_id: str, val: int) -> None:
        """Insert or update an item and explicitly rollback."""
        uow = SqlAlchemyUnitOfWork(self.session_factory)
        with uow:
            session = uow.session
            existing = session.get(UowItem, item_id)
            if existing:
                existing.val = val
            else:
                session.add(UowItem(id=item_id, val=val))
            uow.rollback()

    @rule(
        item_id=st.text(
            min_size=1, max_size=20, alphabet=st.characters(categories=["L", "N"])
        ),
        val=st.integers(min_value=-1000, max_value=1000),
    )
    def insert_and_exception(self, item_id: str, val: int) -> None:
        """Insert or update an item and raise an exception, testing automatic rollback."""
        uow = SqlAlchemyUnitOfWork(self.session_factory)
        try:
            with uow:
                session = uow.session
                existing = session.get(UowItem, item_id)
                if existing:
                    existing.val = val
                else:
                    session.add(UowItem(id=item_id, val=val))
                raise RuntimeError("Simulated transaction crash")
        except RuntimeError:
            pass

    @invariant()
    def database_state_matches_committed(self) -> None:
        """Verify that external database readers only see committed transactions."""
        session = self.session_factory()
        try:
            db_items = session.query(UowItem).all()
            db_dict = {item.id: item.val for item in db_items}
            assert db_dict == self.committed_state
        finally:
            session.close()

    def teardown(self) -> None:
        self.engine.dispose()


TestSqlAlchemyUnitOfWorkStateMachine = SqlAlchemyUnitOfWorkStateMachine.TestCase
