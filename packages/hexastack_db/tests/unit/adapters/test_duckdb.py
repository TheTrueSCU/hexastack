"""Unit tests for embedded DuckDB OLAP analytics repository adapter."""

import contextlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import duckdb
import pyarrow as pa
import pytest

from hexastack_db.adapters.duckdb import (
    AsyncDuckDbRepository,
    DuckDbRepository,
    _py_type_to_duckdb,
    _require_duckdb,
)
from hexastack_db.domain.exceptions import (
    DatabaseConnectionError,
    DatabaseError,
    UniqueConstraintViolationError,
)


@dataclass
class AnalyticsMetric:
    """Sample domain model for testing DuckDB repository operations."""

    id: str
    tenant_id: str
    metric_name: str
    value: float


@dataclass
class ComplexMetric:
    """Model covering diverse python type annotations."""

    id: str
    count: int
    is_active: bool
    payload: bytes
    tags: list[str]
    metadata: dict[str, str]


def test_require_duckdb_missing():
    """Verify informative ImportError is raised when duckdb is missing."""
    with (
        patch.dict("sys.modules", {"duckdb": None}),
        pytest.raises(ImportError, match="duckdb is required for DuckDbRepository"),
    ):
        _require_duckdb()


def test_py_type_to_duckdb_mappings():
    """Verify python types are mapped to valid DuckDB SQL types."""
    assert _py_type_to_duckdb(int) == "BIGINT"
    assert _py_type_to_duckdb(float) == "DOUBLE"
    assert _py_type_to_duckdb(bool) == "BOOLEAN"
    assert _py_type_to_duckdb(str) == "VARCHAR"
    assert _py_type_to_duckdb(bytes) == "BLOB"
    assert _py_type_to_duckdb(list) == "JSON"
    assert _py_type_to_duckdb(dict) == "JSON"
    assert _py_type_to_duckdb(object) == "VARCHAR"


def test_duckdb_repository_init_and_properties():
    """Verify in-memory initialization, table name derivation, and existing connection."""
    raw_conn = duckdb.connect(":memory:")
    repo = DuckDbRepository[AnalyticsMetric, str](
        database=raw_conn,
        model_cls=AnalyticsMetric,
        id_column="id",
    )
    try:
        assert repo.table_name == "analyticsmetric"
        assert repo.connection is raw_conn
    finally:
        repo.close()


def test_duckdb_repository_complex_schema_creation():
    """Verify complex model annotations create valid table structure."""
    repo = DuckDbRepository[ComplexMetric, str](
        database=":memory:",
        model_cls=ComplexMetric,
        id_column="id",
    )
    with repo:
        assert repo.table_name == "complexmetric"
        item = ComplexMetric(
            id="c-1",
            count=10,
            is_active=True,
            payload=b"bytes-data",
            tags=["a", "b"],
            metadata={"env": "prod"},
        )
        repo.add(item)
        fetched = repo.get_by_id("c-1")
        assert fetched is not None
        assert fetched.count == 10
        assert fetched.is_active is True


def test_duckdb_repository_dict_entity_operations():
    """Verify dict-based repository operations when model_cls is omitted."""
    repo = DuckDbRepository[dict, str](
        database=":memory:",
        table_name="raw_events",
        id_column="id",
    )
    with repo:
        repo.add({"id": "evt-1", "data": '{"key": "value"}'})
        repo.add_many([{"id": "evt-2", "data": '{"key": "value2"}'}])
        assert repo.count() == 2
        item = repo.get_by_id("evt-1")
        assert item is not None
        assert item["id"] == "evt-1"


def test_duckdb_repository_crud_operations():
    """Verify add, get_by_id, list_all, count, and remove operations."""
    repo = DuckDbRepository[AnalyticsMetric, str](
        database=":memory:",
        model_cls=AnalyticsMetric,
        id_column="id",
    )
    with repo:
        m1 = AnalyticsMetric(
            id="m-1", tenant_id="tenant-a", metric_name="latency_ms", value=42.5
        )
        m2 = AnalyticsMetric(
            id="m-2", tenant_id="tenant-a", metric_name="cpu_pct", value=88.0
        )
        m3 = AnalyticsMetric(
            id="m-3", tenant_id="tenant-b", metric_name="latency_ms", value=12.0
        )

        repo.add(m1)
        repo.add_many([m2, m3])
        repo.add_many([])  # Empty batch branch

        cnt = repo.count()
        assert cnt == 3

        fetched = repo.get_by_id("m-1")
        assert fetched is not None
        assert fetched.id == "m-1"
        assert fetched.metric_name == "latency_ms"
        assert fetched.value == 42.5

        non_existent = repo.get_by_id("non-existent")
        assert non_existent is None

        all_items = repo.list_all()
        assert len(all_items) == 3

        paginated = repo.list_all(limit=2, offset=1)
        assert len(paginated) == 2

        repo.remove("m-1")
        cnt_after = repo.count()
        assert cnt_after == 2
        assert repo.get_by_id("m-1") is None


def test_duckdb_repository_unique_constraint_violation():
    """Verify unique constraint violation translates to UniqueConstraintViolationError."""
    repo = DuckDbRepository[AnalyticsMetric, str](
        database=":memory:",
        model_cls=AnalyticsMetric,
        id_column="id",
    )
    with repo:
        m1 = AnalyticsMetric(id="dup-1", tenant_id="t1", metric_name="m1", value=1.0)
        m2 = AnalyticsMetric(id="dup-1", tenant_id="t1", metric_name="m2", value=2.0)

        repo.add(m1)
        with pytest.raises(UniqueConstraintViolationError):
            repo.add(m2)

        with pytest.raises(UniqueConstraintViolationError):
            repo.add_many([m2])


def test_duckdb_repository_query_and_aggregations():
    """Verify analytical query execution, scalar aggregations, and entity mapping."""
    repo = DuckDbRepository[AnalyticsMetric, str](
        database=":memory:",
        model_cls=AnalyticsMetric,
        id_column="id",
    )
    with repo:
        metrics = [
            AnalyticsMetric(
                id=f"m-{i}",
                tenant_id="tenant-1",
                metric_name="reqs",
                value=float(i * 10),
            )
            for i in range(1, 6)
        ]
        repo.add_many(metrics)

        # Raw query
        rows = repo.query(
            "SELECT tenant_id, avg(value) as avg_val FROM analyticsmetric GROUP BY tenant_id"
        )
        assert len(rows) == 1
        assert rows[0]["tenant_id"] == "tenant-1"
        assert rows[0]["avg_val"] == 30.0

        # Scalar query
        max_val = repo.query_scalar("SELECT max(value) FROM analyticsmetric")
        assert max_val == 50.0

        empty_scalar = repo.query_scalar(
            "SELECT max(value) FROM analyticsmetric WHERE value > 1000"
        )
        assert empty_scalar is None

        # Query entities
        filtered = repo.query_entities(
            "SELECT * FROM analyticsmetric WHERE value > ? ORDER BY value",
            [25.0],
        )
        assert len(filtered) == 3
        assert [m.id for m in filtered] == ["m-3", "m-4", "m-5"]


def test_duckdb_repository_arrow_and_polars_exports():
    """Verify query_arrow, register_arrow, and optional dataframe integrations."""
    repo = DuckDbRepository[AnalyticsMetric, str](
        database=":memory:",
        model_cls=AnalyticsMetric,
        id_column="id",
    )
    with repo:
        repo.add(
            AnalyticsMetric(id="df-1", tenant_id="t1", metric_name="cost", value=99.9)
        )

        arrow_tbl = repo.query_arrow("SELECT * FROM analyticsmetric")
        assert hasattr(arrow_tbl, "num_rows")
        assert arrow_tbl.num_rows == 1

        # Register external Arrow table
        sample_tbl = pa.Table.from_pydict({"num": [1, 2, 3], "label": ["a", "b", "c"]})
        repo.register_view("arrow_view", sample_tbl)
        arrow_res = repo.query("SELECT * FROM arrow_view ORDER BY num")
        assert len(arrow_res) == 3
        assert arrow_res[0]["label"] == "a"

        # Test execute DDL
        repo.execute("CREATE TABLE test_exec (id INT)")
        repo.execute("INSERT INTO test_exec VALUES (?)", [42])
        assert repo.query_scalar("SELECT id FROM test_exec") == 42


def test_duckdb_repository_dataframe_and_polars_error_handling():
    """Verify query_df and query_polars error wrapping when optional libraries missing."""
    repo = DuckDbRepository[AnalyticsMetric, str](
        database=":memory:",
        model_cls=AnalyticsMetric,
        id_column="id",
    )
    with repo:
        try:
            repo.query_df("SELECT * FROM analyticsmetric")
        except DatabaseError as exc:
            assert "DataFrame query execution failed" in str(exc)

        try:
            repo.query_polars("SELECT * FROM analyticsmetric")
        except DatabaseError as exc:
            assert "Polars query execution failed" in str(exc)


def test_duckdb_repository_views_parquet_and_csv(tmp_path: Path):
    """Verify view registration, Parquet export/import, and CSV export."""
    repo = DuckDbRepository[AnalyticsMetric, str](
        database=":memory:",
        model_cls=AnalyticsMetric,
        id_column="id",
    )
    with repo:
        repo.add_many(
            [
                AnalyticsMetric(
                    id="v-1", tenant_id="t1", metric_name="cpu", value=10.0
                ),
                AnalyticsMetric(
                    id="v-2", tenant_id="t1", metric_name="mem", value=20.0
                ),
            ]
        )

        # Register SQL View
        repo.register_view(
            "high_metrics", "SELECT * FROM analyticsmetric WHERE value >= 20.0"
        )
        view_rows = repo.query("SELECT * FROM high_metrics")
        assert len(view_rows) == 1
        assert view_rows[0]["id"] == "v-2"

        # Export Parquet
        parquet_path = tmp_path / "metrics.parquet"
        repo.export_parquet("analyticsmetric", str(parquet_path))
        assert parquet_path.exists()

        # Register Parquet View and query it
        repo.register_parquet("parquet_metrics", str(parquet_path))
        pq_rows = repo.query("SELECT * FROM parquet_metrics")
        assert len(pq_rows) == 2

        # Export CSV
        csv_path = tmp_path / "metrics.csv"
        repo.export_csv("analyticsmetric", str(csv_path))
        assert csv_path.exists()
        csv_content = csv_path.read_text()
        assert "v-1" in csv_content
        assert "v-2" in csv_content


def test_duckdb_repository_attach_sqlite(tmp_path: Path):
    """Verify attaching an external SQLite database into DuckDB."""
    sqlite_file = tmp_path / "test.db"
    conn = sqlite3.connect(sqlite_file)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob')")
    conn.commit()
    conn.close()

    repo = DuckDbRepository[dict, int](
        database=":memory:",
        table_name="local_table",
        auto_create_table=False,
    )
    with repo:
        repo.attach_sqlite(sqlite_file, schema_name="ext_sqlite")
        rows = repo.query("SELECT * FROM ext_sqlite.users ORDER BY id")
        assert len(rows) == 2
        assert rows[0]["name"] == "Alice"
        assert rows[1]["name"] == "Bob"


def test_duckdb_repository_connection_error():
    """Verify invalid database target raises DatabaseConnectionError."""
    with (
        patch("duckdb.connect", side_effect=RuntimeError("Invalid disk path")),
        pytest.raises(DatabaseConnectionError),
    ):
        DuckDbRepository(database="/invalid/nonexistent/path/db.duckdb")


def test_duckdb_repository_invalid_queries_raise_database_error():
    """Verify malformed SQL raises DatabaseError."""
    repo = DuckDbRepository[AnalyticsMetric, str](
        database=":memory:",
        model_cls=AnalyticsMetric,
    )
    with repo:
        with pytest.raises(DatabaseError):
            repo.query("SELECT * FROM nonexistent_table")

        with pytest.raises(DatabaseError):
            repo.execute("INVALID SQL STATEMENT")


@pytest.mark.asyncio
async def test_async_duckdb_repository_lifecycle_and_crud(tmp_path: Path):
    """Verify AsyncDuckDbRepository asynchronous execution across methods."""
    repo = AsyncDuckDbRepository[AnalyticsMetric, str](
        database=":memory:",
        model_cls=AnalyticsMetric,
        id_column="id",
    )
    async with repo:
        assert repo.sync_repo is not None

        m1 = AnalyticsMetric(
            id="async-1", tenant_id="t-async", metric_name="ops", value=100.0
        )
        m2 = AnalyticsMetric(
            id="async-2", tenant_id="t-async", metric_name="errs", value=2.0
        )

        await repo.add_async(m1)
        await repo.add_many_async([m2])

        cnt = await repo.count_async()
        assert cnt == 2

        fetched = await repo.get_by_id_async("async-1")
        assert fetched is not None
        assert fetched.value == 100.0

        all_items = await repo.list_all_async()
        assert len(all_items) == 2

        scalar = await repo.query_scalar_async("SELECT sum(value) FROM analyticsmetric")
        assert scalar == 102.0

        entities = await repo.query_entities_async(
            "SELECT * FROM analyticsmetric WHERE id = ?", ["async-2"]
        )
        assert len(entities) == 1
        assert entities[0].metric_name == "errs"

        raw_query = await repo.query_async("SELECT count(*) as c FROM analyticsmetric")
        assert raw_query[0]["c"] == 2

        # View and Parquet
        await repo.register_view_async("v_async", "SELECT * FROM analyticsmetric")
        pq_path = tmp_path / "async_metrics.parquet"
        await repo.export_parquet_async("v_async", str(pq_path))
        assert pq_path.exists()

        await repo.register_parquet_async("pq_async", str(pq_path))
        pq_res = await repo.query_async("SELECT * FROM pq_async")
        assert len(pq_res) == 2

        # Async execute and arrow
        await repo.execute_async("CREATE TABLE t_async (x INT)")
        arrow_res = await repo.query_arrow_async("SELECT * FROM pq_async")
        assert hasattr(arrow_res, "num_rows")

        with contextlib.suppress(DatabaseError):
            await repo.query_df_async("SELECT * FROM pq_async")

        with contextlib.suppress(DatabaseError):
            await repo.query_polars_async("SELECT * FROM pq_async")

        await repo.remove_async("async-1")
        cnt_after = await repo.count_async()
        assert cnt_after == 1


def test_duckdb_repository_closed_access_error():
    """Verify accessing methods on a closed repository raises DatabaseError."""
    repo = DuckDbRepository[dict, str](database=":memory:")
    repo.close()
    with pytest.raises(DatabaseError, match="is closed"):
        repo.get_by_id("1")


def test_duckdb_repository_entity_serialization_variants():
    """Verify _entity_to_dict and _dict_to_entity handle diverse object types."""

    class PlainObj:
        def __init__(self, id: str, value: int):
            self.id = id
            self.value = value

    class PydanticLike:
        def __init__(self, id: str, value: int):
            self.id = id
            self.value = value

        def model_dump(self):
            return {"id": self.id, "value": self.value}

        @classmethod
        def model_validate(cls, data):
            return cls(id=data["id"], value=data["value"])

    repo_plain = DuckDbRepository[PlainObj, str](
        database=":memory:",
        model_cls=PlainObj,
        auto_create_table=False,
    )
    repo_plain.execute("CREATE TABLE plainobj (id VARCHAR PRIMARY KEY, value BIGINT)")
    repo_plain.add(PlainObj("p-1", 42))
    fetched_p = repo_plain.get_by_id("p-1")
    assert fetched_p is not None
    assert fetched_p.value == 42
    repo_plain.close()

    repo_pydantic = DuckDbRepository[PydanticLike, str](
        database=":memory:",
        model_cls=PydanticLike,
        auto_create_table=False,
    )
    repo_pydantic.execute(
        "CREATE TABLE pydanticlike (id VARCHAR PRIMARY KEY, value BIGINT)"
    )
    repo_pydantic.add(PydanticLike("py-1", 99))
    fetched_py = repo_pydantic.get_by_id("py-1")
    assert fetched_py is not None
    assert fetched_py.value == 99
    repo_pydantic.close()

    # Unsupported entity type raises ValueError
    repo_dict = DuckDbRepository[dict, str](
        database=":memory:", auto_create_table=False
    )
    with pytest.raises(ValueError, match="Unsupported entity type"):
        repo_dict._entity_to_dict(12345)
    repo_dict.close()


def test_duckdb_repository_error_branches():
    """Verify error wrapping across repository methods when internal queries fail."""
    from unittest.mock import MagicMock

    repo = DuckDbRepository[dict, str](database=":memory:", auto_create_table=False)
    mock_conn = MagicMock()
    repo._conn = mock_conn

    # Ensure table creation error
    mock_conn.execute.side_effect = RuntimeError("DDL failed")
    with pytest.raises(DatabaseError, match="Failed to ensure table"):
        repo._ensure_table()

    # get_by_id error
    mock_conn.execute.side_effect = RuntimeError("Read failed")
    with pytest.raises(DatabaseError, match="Failed to query entity"):
        repo.get_by_id("1")

    # remove error
    mock_conn.execute.side_effect = RuntimeError("Delete failed")
    with pytest.raises(DatabaseError, match="Failed to delete entity"):
        repo.remove("1")

    # list_all error
    mock_conn.execute.side_effect = RuntimeError("List failed")
    with pytest.raises(DatabaseError, match="Failed to list all"):
        repo.list_all()

    # scalar query error
    mock_conn.execute.side_effect = RuntimeError("Scalar failed")
    with pytest.raises(DatabaseError, match="Scalar query execution failed"):
        repo.query_scalar("SELECT 1")

    # arrow query error
    mock_conn.sql.side_effect = RuntimeError("Arrow failed")
    with pytest.raises(DatabaseError, match="Arrow query execution failed"):
        repo.query_arrow("SELECT 1")

    # register_view error
    mock_conn.execute.side_effect = RuntimeError("View failed")
    with pytest.raises(DatabaseError, match="Failed to register view"):
        repo.register_view("v_fail", "SELECT 1")
