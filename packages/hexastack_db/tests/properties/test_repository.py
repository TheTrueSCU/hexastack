from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from hexastack_db.adapters.repository import SqlAlchemyRepository


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


@given(
    vec=st.lists(
        st.floats(
            min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False
        ),
        min_size=2,
        max_size=32,
    )
)
def test_hypothesis_cosine_similarity_reflexivity_and_bounds(vec: list[float]):
    """Cosine similarity of non-zero vector with itself is 1.0; zero vector is 0.0."""
    import math

    from hexastack_db.adapters.vector import _cosine_similarity

    norm = math.sqrt(sum(x * x for x in vec))
    sim_self = _cosine_similarity(vec, vec)

    if norm == 0.0:
        assert sim_self == 0.0
    else:
        assert math.isclose(sim_self, 1.0, rel_tol=1e-4, abs_tol=1e-4)

    zero_vec = [0.0] * len(vec)
    assert _cosine_similarity(vec, zero_vec) == 0.0
    assert _cosine_similarity(zero_vec, vec) == 0.0


@given(
    v1=st.lists(
        st.floats(
            min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
        min_size=4,
        max_size=4,
    ),
    v2=st.lists(
        st.floats(
            min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
        min_size=4,
        max_size=4,
    ),
)
def test_hypothesis_cosine_similarity_symmetry_and_range(
    v1: list[float], v2: list[float]
):
    """Cosine similarity is commutative: sim(a, b) == sim(b, a), bounded in [-1.0, 1.0]."""
    import math

    from hexastack_db.adapters.vector import _cosine_similarity

    sim_12 = _cosine_similarity(v1, v2)
    sim_21 = _cosine_similarity(v2, v1)
    assert math.isclose(sim_12, sim_21, rel_tol=1e-5, abs_tol=1e-5)
    assert -1.0001 <= sim_12 <= 1.0001


@given(
    dim=st.integers(min_value=2, max_value=8),
    records=st.lists(
        st.tuples(
            st.text(
                min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz0123456789"
            ),
            st.lists(
                st.floats(
                    min_value=-10.0,
                    max_value=10.0,
                    allow_nan=False,
                    allow_infinity=False,
                ),
                min_size=2,
                max_size=8,
            ),
            st.dictionaries(
                st.text(min_size=1, max_size=5),
                st.text(min_size=1, max_size=10),
                max_size=3,
            ),
        ),
        min_size=1,
        max_size=10,
        unique_by=lambda r: r[0],
    ),
)
def test_hypothesis_vector_adapter_storage_and_ordering_invariants(
    dim: int,
    records: list[tuple[str, list[float], dict[str, str]]],
):
    """Verify vector upsert, get, search ordering, and delete invariants under property fuzzing."""
    from hexastack_db.adapters.vector import PgVectorStoreAdapter
    from hexastack_db.infra.config import PgVectorConfig

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = sessionmaker(bind=engine)
    config = PgVectorConfig(table_name="hypo_vectors", dimension=dim)
    adapter = PgVectorStoreAdapter(session_factory=factory, config=config)
    adapter.create_table()

    # 1. Upsert all valid-dimension vectors
    valid_records = []
    for vid, emb_raw, meta in records:
        emb = (emb_raw[:dim] + [0.0] * dim)[:dim]  # normalize to dim
        adapter.upsert(vid, emb, meta)
        valid_records.append((vid, emb, meta))

    # 2. Get verification
    for vid, emb, meta in valid_records:
        res = adapter.get(vid)
        assert res is not None
        fetched_emb, fetched_meta = res
        assert fetched_emb == emb
        assert fetched_meta == meta

    # 3. Search ordering invariant: results must be monotonically non-increasing by score
    query_vec = [1.0] * dim
    results = adapter.search(query_vec, limit=len(valid_records))
    scores = [r["_score"] for r in results]
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1]

    # 4. Deletion
    for vid, _, _ in valid_records:
        deleted = adapter.delete(vid)
        assert deleted is True
        assert adapter.get(vid) is None
