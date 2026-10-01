"""Hypothesis RuleBasedStateMachine dual-implementation oracle tests for SqlAlchemyRepository.

Notes/Architectural Intent:
    Validates that SqlAlchemyRepository (production persistence adapter) and
    InMemoryRepository (in-memory reference adapter) maintain exact state and
    behavioral parity across arbitrary sequences of CRUD, filtering, pagination,
    and batch mutations under Hypothesis fuzz generation.
"""

from dataclasses import dataclass

from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    rule,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from hexastack_core.adapters.repository import InMemoryRepository
from hexastack_db.adapters.repository import SqlAlchemyRepository
from hexastack_db.domain.exceptions import UniqueConstraintViolationError


class Base(DeclarativeBase):
    """Base declarative class for repository oracle testing."""


class OracleItemModel(Base):
    """Declarative model for database persistence under oracle testing."""

    __tablename__ = "oracle_items"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    category: Mapped[str] = mapped_column(nullable=False)
    value: Mapped[int] = mapped_column(nullable=False)


@dataclass(frozen=True)
class ItemData:
    """Pure domain entity representation for reference oracle storage."""

    id: str
    name: str
    category: str
    value: int


ID_STRATEGY = st.sampled_from(
    [
        "item_1",
        "item_2",
        "item_3",
        "item_4",
        "item_5",
        "item_6",
        "item_7",
        "item_8",
    ]
)
CATEGORY_STRATEGY = st.sampled_from(["alpha", "beta", "gamma", "delta"])
NAME_STRATEGY = st.text(
    min_size=1, max_size=20, alphabet=st.characters(categories=["L"])
)
VALUE_STRATEGY = st.integers(min_value=-1000, max_value=1000)


class RepositoryOracleStateMachine(RuleBasedStateMachine):
    """Hypothesis state machine verifying dual-implementation repository parity.

    Notes/Architectural Intent:
        Exercises arbitrary interleaved CRUD sequences, uniqueness constraints,
        updates, deletions, filtering, and bulk additions, verifying that
        SqlAlchemyRepository and InMemoryRepository yield identical results.
    """

    def __init__(self) -> None:
        """Initialize state machine, in-memory SQLite database, and dual repositories."""
        super().__init__()
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.session: Session = self.session_factory()
        self.sql_repo = SqlAlchemyRepository(self.session, OracleItemModel)
        self.oracle_repo: InMemoryRepository[ItemData, str] = InMemoryRepository(
            id_attr="id"
        )

    def teardown(self) -> None:
        """Cleanly dispose database connections and session resources."""
        self.session.close()
        self.engine.dispose()

    @rule(
        item_id=ID_STRATEGY,
        name=NAME_STRATEGY,
        category=CATEGORY_STRATEGY,
        value=VALUE_STRATEGY,
    )
    def add_item(self, item_id: str, name: str, category: str, value: int) -> None:
        """Add an item or verify duplicate rejection parity.

        Args:
            item_id: Unique identifier for the item.
            name: Human-readable name.
            category: Classification category.
            value: Numerical metric payload.
        """
        item_exists = item_id in self.oracle_repo._store
        if item_exists:
            dup_model = OracleItemModel(
                id=item_id, name=name, category=category, value=value
            )
            try:
                self.sql_repo.add(dup_model)
                self.session.commit()
                err_msg = (
                    "Expected UniqueConstraintViolationError on duplicate item addition"
                )
                raise AssertionError(err_msg)
            except UniqueConstraintViolationError:
                self.session.rollback()
        else:
            model = OracleItemModel(
                id=item_id, name=name, category=category, value=value
            )
            self.sql_repo.add(model)
            self.session.commit()
            data = ItemData(id=item_id, name=name, category=category, value=value)
            self.oracle_repo.add(data)

            sql_cnt = self.sql_repo.count()
            orc_cnt = len(self.oracle_repo.all())
            assert sql_cnt == orc_cnt

    @rule(
        item_id=ID_STRATEGY,
        name=NAME_STRATEGY,
        category=CATEGORY_STRATEGY,
        value=VALUE_STRATEGY,
    )
    def update_item(self, item_id: str, name: str, category: str, value: int) -> None:
        """Update or upsert an item across both repositories.

        Args:
            item_id: Unique identifier for the item.
            name: Updated name.
            category: Updated category.
            value: Updated value.
        """
        model = OracleItemModel(id=item_id, name=name, category=category, value=value)
        self.sql_repo.update(model)
        self.session.commit()

        data = ItemData(id=item_id, name=name, category=category, value=value)
        self.oracle_repo.add(data)

        sql_item = self.sql_repo.get(item_id)
        orc_item = self.oracle_repo.get_by_id(item_id)
        assert sql_item is not None
        assert orc_item is not None
        assert sql_item.id == orc_item.id
        assert sql_item.name == orc_item.name
        assert sql_item.category == orc_item.category
        assert sql_item.value == orc_item.value

    @rule(item_id=ID_STRATEGY)
    def delete_item(self, item_id: str) -> None:
        """Delete an item and verify outcome parity.

        Args:
            item_id: Target item identifier.
        """
        was_present = item_id in self.oracle_repo._store
        deleted = self.sql_repo.delete(item_id)
        self.session.commit()
        self.oracle_repo.remove(item_id)

        assert deleted is was_present

        sql_item = self.sql_repo.get(item_id)
        orc_item = self.oracle_repo.get_by_id(item_id)
        assert sql_item is None
        assert orc_item is None

    @rule(item_id=ID_STRATEGY)
    def get_item(self, item_id: str) -> None:
        """Retrieve an item and verify equality across all fields.

        Args:
            item_id: Identifier to inspect.
        """
        sql_item = self.sql_repo.get(item_id)
        orc_item = self.oracle_repo.get_by_id(item_id)

        sql_is_none = sql_item is None
        orc_is_none = orc_item is None
        assert sql_is_none is orc_is_none

        if sql_item is not None and orc_item is not None:
            assert sql_item.id == orc_item.id
            assert sql_item.name == orc_item.name
            assert sql_item.category == orc_item.category
            assert sql_item.value == orc_item.value

    @rule(category=CATEGORY_STRATEGY)
    def count_and_filter(self, category: str) -> None:
        """Verify filtered count query parity.

        Args:
            category: Filter category.
        """
        sql_count = self.sql_repo.count(category=category)
        orc_count = sum(
            1 for item in self.oracle_repo.all() if item.category == category
        )
        assert sql_count == orc_count

        total_sql = self.sql_repo.count()
        total_orc = len(self.oracle_repo.all())
        assert total_sql == total_orc

    @rule(category=CATEGORY_STRATEGY)
    def list_by_category(self, category: str) -> None:
        """Verify filtered list query ID set equivalence.

        Args:
            category: Category to query.
        """
        sql_records = self.sql_repo.list(offset=0, limit=1000, category=category)
        sql_ids = {x.id for x in sql_records}
        orc_ids = {
            item.id for item in self.oracle_repo.all() if item.category == category
        }
        assert sql_ids == orc_ids

    @rule(
        batch=st.lists(
            st.tuples(
                st.text(
                    min_size=2,
                    max_size=10,
                    alphabet=st.characters(categories=["L", "N"]),
                ),
                NAME_STRATEGY,
                CATEGORY_STRATEGY,
                VALUE_STRATEGY,
            ),
            min_size=1,
            max_size=5,
        )
    )
    def add_many_items(
        self,
        batch: list[tuple[str, str, str, int]],
    ) -> None:
        """Batch-insert multiple new entities and verify count parity.

        Args:
            batch: List of tuple parameters for new entities.
        """
        seen_ids: set[str] = set(self.oracle_repo._store.keys())
        unique_batch: list[ItemData] = []
        for raw_id, name, cat, val in batch:
            batch_id = f"batch_{raw_id}"
            if batch_id not in seen_ids:
                seen_ids.add(batch_id)
                unique_batch.append(
                    ItemData(id=batch_id, name=name, category=cat, value=val)
                )

        if not unique_batch:
            return

        models = [
            OracleItemModel(id=x.id, name=x.name, category=x.category, value=x.value)
            for x in unique_batch
        ]
        self.sql_repo.add_many(models)
        self.session.commit()

        for data in unique_batch:
            self.oracle_repo.add(data)

        sql_cnt = self.sql_repo.count()
        orc_cnt = len(self.oracle_repo.all())
        assert sql_cnt == orc_cnt

    @invariant()
    def repository_state_equivalence(self) -> None:
        """Invariant: both repositories must store identical records at all times."""
        sql_count = self.sql_repo.count()
        all_oracle = self.oracle_repo.all()
        oracle_count = len(all_oracle)
        assert sql_count == oracle_count

        for orc_item in all_oracle:
            sql_item = self.sql_repo.get(orc_item.id)
            assert sql_item is not None
            assert sql_item.name == orc_item.name
            assert sql_item.category == orc_item.category
            assert sql_item.value == orc_item.value


TestRepositoryOracle = RepositoryOracleStateMachine.TestCase
