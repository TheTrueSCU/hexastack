"""Performance microbenchmarks for SQLAlchemy repository adapter.

Notes/Architectural Intent:
    Measures latency and throughput of SqlAlchemyRepository CRUD operations
    over in-memory SQLite, quantifying ORM mapping and query execution overhead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from hexastack_db.adapters.repository import SqlAlchemyRepository

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture


class _BenchmarkBase(DeclarativeBase):
    pass


class _BenchItem(_BenchmarkBase):
    __tablename__ = "bench_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(unique=True)
    sku: Mapped[str]


def _setup_bench_session() -> tuple[Session, SqlAlchemyRepository[_BenchItem, int]]:
    """Create in-memory SQLite engine and populated benchmark repository."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
    )
    _BenchmarkBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    repo = SqlAlchemyRepository(session=session, model_cls=_BenchItem)

    # Seed 100 items
    items = [_BenchItem(name=f"item_{i}", sku=f"SKU-{i:04d}") for i in range(100)]
    repo.add_many(items)
    session.commit()
    return session, repo


def test_perf_repository_get_by_id(benchmark: BenchmarkFixture) -> None:
    """Benchmark single-entity primary key lookup latency.

    Args:
        benchmark: pytest-benchmark fixture.

    Notes/Architectural Intent:
        Quantifies raw identity-map and session cache query resolution latency.
    """
    _session, repo = _setup_bench_session()

    res = benchmark(repo.get_by_id, 42)
    assert res is not None
    res_id = res.id
    assert res_id == 42


def test_perf_repository_list(benchmark: BenchmarkFixture) -> None:
    """Benchmark paginated entity list query latency.

    Args:
        benchmark: pytest-benchmark fixture.

    Notes/Architectural Intent:
        Quantifies SQL generation and hydration overhead for multi-record result sets.
    """
    _session, repo = _setup_bench_session()

    res = benchmark(repo.list, limit=20, offset=10)
    count = len(res)
    assert count == 20


def test_perf_repository_add(benchmark: BenchmarkFixture) -> None:
    """Benchmark new entity insertion and session flush latency.

    Args:
        benchmark: pytest-benchmark fixture.

    Notes/Architectural Intent:
        Quantifies ORM instance tracking and INSERT statement execution overhead.
    """
    session, repo = _setup_bench_session()
    counter = [1000]

    def _do_add() -> _BenchItem:
        counter[0] += 1
        item = _BenchItem(name=f"bench_item_{counter[0]}", sku=f"SKU-{counter[0]}")
        repo.add(item)
        return item

    res = benchmark(_do_add)
    assert res.id is not None
