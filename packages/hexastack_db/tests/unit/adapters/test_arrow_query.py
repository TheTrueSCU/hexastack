import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from hexastack_db.adapters.analytics import PolarsColumnarAdapter
from hexastack_db.adapters.arrow_query import ArrowQueryHandler


@pytest.fixture
def sqlite_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE logs ("
                "  id INTEGER PRIMARY KEY,"
                "  level VARCHAR(10),"
                "  message VARCHAR(255)"
                ")"
            )
        )
        conn.execute(
            text(
                "INSERT INTO logs (level, message) VALUES "
                "('INFO', 'Server started'), "
                "('WARN', 'High memory usage'), "
                "('ERROR', 'Connection failed')"
            )
        )
    return engine


def test_arrow_query_handler_with_engine(sqlite_engine):
    handler = ArrowQueryHandler(engine_or_connection=sqlite_engine)

    # Arrow
    table = handler.query_arrow("SELECT * FROM logs ORDER BY id")
    assert table.num_rows == 3
    assert "level" in table.column_names

    # Polars
    df = handler.query_polars("SELECT * FROM logs WHERE level = 'ERROR'")
    assert df.height == 1
    assert df["message"][0] == "Connection failed"

    # Export
    export_res = handler.query_export("SELECT * FROM logs", format="parquet")
    assert export_res.format == "parquet"
    assert export_res.metadata.num_rows == 3


async def test_arrow_query_handler_async(sqlite_engine):
    adapter = PolarsColumnarAdapter(engine_or_connection=sqlite_engine)
    handler = ArrowQueryHandler(adapter=adapter)

    table = await handler.query_arrow_async("SELECT * FROM logs")
    assert table.num_rows == 3

    df = await handler.query_polars_async("SELECT * FROM logs WHERE level = 'WARN'")
    assert df.height == 1

    exp = await handler.query_export_async("SELECT * FROM logs", format="json")
    assert exp.format == "json"
    assert b"Server started" in exp.data
