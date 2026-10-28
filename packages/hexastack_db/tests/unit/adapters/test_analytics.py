import time
from typing import Any, cast

import duckdb
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from hexastack_db.adapters.analytics import PolarsColumnarAdapter
from hexastack_db.domain.exceptions import ColumnarQueryError


@pytest.fixture
def sqlite_engine():
    """Create in-memory SQLite engine with seeded telemetry data using StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE metrics ("
                "  id INTEGER PRIMARY KEY,"
                "  service VARCHAR(50),"
                "  latency REAL,"
                "  status_code INTEGER"
                ")"
            )
        )
        conn.execute(
            text(
                "INSERT INTO metrics (service, latency, status_code) VALUES "
                "('auth', 12.4, 200), "
                "('payment', 45.1, 201), "
                "('orders', 8.2, 200), "
                "('inventory', 95.0, 500)"
            )
        )
    return engine


def test_polars_columnar_adapter_sqlite_sync(sqlite_engine):
    adapter = PolarsColumnarAdapter(engine_or_connection=sqlite_engine)

    df = adapter.execute_polars("SELECT * FROM metrics ORDER BY id")
    assert df.height == 4
    assert df.width == 4
    assert "service" in df.columns
    assert df["service"].to_list() == ["auth", "payment", "orders", "inventory"]

    # Parameterized query
    df_filtered = adapter.execute_polars(
        "SELECT * FROM metrics WHERE status_code = :status",
        params={"status": 200},
    )
    assert df_filtered.height == 2

    # Arrow Table
    table = adapter.execute_arrow("SELECT * FROM metrics ORDER BY id")
    assert table.num_rows == 4
    assert table.num_columns == 4


async def test_polars_columnar_adapter_sqlite_async(sqlite_engine):
    adapter = PolarsColumnarAdapter(engine_or_connection=sqlite_engine)

    df = await adapter.execute_polars_async("SELECT * FROM metrics ORDER BY id")
    assert df.height == 4

    table = await adapter.execute_arrow_async(
        "SELECT * FROM metrics WHERE latency > :min_lat", params={"min_lat": 20.0}
    )
    assert table.num_rows == 2


def test_polars_columnar_adapter_exports(sqlite_engine, tmp_path):
    adapter = PolarsColumnarAdapter(engine_or_connection=sqlite_engine)
    query = "SELECT * FROM metrics ORDER BY id"

    # Parquet
    parquet_res = adapter.export(query, format="parquet")
    assert parquet_res.format == "parquet"
    assert parquet_res.metadata.num_rows == 4
    assert parquet_res.metadata.byte_size is not None
    assert parquet_res.metadata.byte_size > 0
    p_file = parquet_res.to_file(tmp_path / "metrics.parquet")
    assert p_file.exists()

    # Arrow IPC (Feather)
    ipc_res = adapter.export(query, format="arrow_ipc")
    assert ipc_res.format == "arrow_ipc"
    assert ipc_res.metadata.num_rows == 4
    i_file = ipc_res.to_file(tmp_path / "metrics.arrow")
    assert i_file.exists()

    # JSON
    json_res = adapter.export(query, format="json")
    assert json_res.format == "json"
    assert b"auth" in json_res.data

    # CSV
    csv_res = adapter.export(query, format="csv")
    assert csv_res.format == "csv"
    assert b"service,latency,status_code" in csv_res.data


async def test_polars_columnar_adapter_export_async(sqlite_engine):
    adapter = PolarsColumnarAdapter(engine_or_connection=sqlite_engine)
    res = await adapter.export_async("SELECT * FROM metrics", format="parquet")
    assert res.metadata.num_rows == 4


def test_polars_columnar_adapter_duckdb():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE sales (region VARCHAR, amount DOUBLE)")
    conn.execute("INSERT INTO sales VALUES ('north', 100.5), ('south', 250.0)")

    adapter = PolarsColumnarAdapter(engine_or_connection=conn)
    df = adapter.execute_polars("SELECT * FROM sales ORDER BY region")
    assert df.height == 2
    assert df["region"].to_list() == ["north", "south"]

    tbl = adapter.execute_arrow("SELECT * FROM sales")
    assert tbl.num_rows == 2


def test_polars_columnar_adapter_errors():
    # No connection provided
    empty_adapter = PolarsColumnarAdapter()
    with pytest.raises(ColumnarQueryError) as exc_info:
        empty_adapter.execute_polars("SELECT 1")
    assert "No database connection" in str(exc_info.value)

    # Invalid SQL
    engine = create_engine("sqlite:///:memory:")
    bad_adapter = PolarsColumnarAdapter(engine_or_connection=engine)
    with pytest.raises(ColumnarQueryError):
        bad_adapter.execute_polars("SELECT * FROM non_existent_table")

    # Unsupported export format
    with pytest.raises(ColumnarQueryError) as exc_fmt:
        bad_adapter.export("SELECT 1", format=cast("Any", "unsupported_format"))
    assert "Unsupported columnar export format" in str(exc_fmt.value)


def test_polars_columnar_adapter_high_throughput_benchmark():
    """Benchmark high-throughput columnar ingestion across 10,000 rows."""
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE large_dataset AS "
                "WITH RECURSIVE cnt(x) AS ("
                "  SELECT 1 "
                "  UNION ALL "
                "  SELECT x+1 FROM cnt WHERE x < 10000"
                ") "
                "SELECT x as id, 'metric_' || (x % 50) as tag, (x * 1.5) as val FROM cnt;"
            )
        )

    adapter = PolarsColumnarAdapter(engine_or_connection=engine)

    start_vector = time.perf_counter()
    df = adapter.execute_polars("SELECT * FROM large_dataset")
    elapsed_vector = time.perf_counter() - start_vector

    assert df.height == 10000
    assert df.width == 3
    # Verify sub-second ingestion
    assert elapsed_vector < 2.0
