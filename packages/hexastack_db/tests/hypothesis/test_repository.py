from hexastack_db.adapters.repository import SqlAlchemyRepository
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


class HypoItem(Base):
    __tablename__ = "hypo_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    value: Mapped[int]


@given(
    names=st.lists(
        st.text(min_size=1, max_size=50), min_size=1, max_size=20, unique=False
    ),
    values=st.lists(
        st.integers(min_value=-10000, max_value=10000), min_size=1, max_size=20
    ),
)
def test_hypothesis_repository_crud_invariants(names: list[str], values: list[int]):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session: Session = session_factory()
    repo = SqlAlchemyRepository(session=session, model_cls=HypoItem)

    # 1. Add batch
    count_to_add = min(len(names), len(values))
    items = [HypoItem(name=names[i], value=values[i]) for i in range(count_to_add)]
    repo.add_many(items)

    assert repo.count() == count_to_add

    # 2. Verify all items retrievable by ID
    for item in items:
        fetched = repo.get(item.id)
        assert fetched is not None
        assert fetched.name == item.name
        assert fetched.value == item.value

    # 3. List matches count
    all_items = repo.list(limit=count_to_add + 10)
    assert len(all_items) == count_to_add

    # 4. Clean deletion
    for item in items:
        deleted = repo.delete(item.id)
        assert deleted is True

    assert repo.count() == 0

    session.close()
    engine.dispose()
