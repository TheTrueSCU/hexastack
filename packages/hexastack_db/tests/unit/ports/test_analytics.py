import inspect
from collections.abc import Sequence
from typing import Any

import polars as pl
import pyarrow as pa
import pytest

from hexastack_db.domain.analytics import (
    ColumnarExportFormat,
    ColumnarExportResult,
    ColumnarProjectionMetadata,
)
from hexastack_db.ports.analytics import PolarsProjectionPort


class DummyPolarsProjectionPort(PolarsProjectionPort):
    def execute_polars(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pl.DataFrame:
        return pl.DataFrame({"id": [1, 2], "name": ["alpha", "beta"]})

    async def execute_polars_async(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pl.DataFrame:
        return self.execute_polars(query, params)

    def execute_arrow(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pa.Table:
        return self.execute_polars(query, params).to_arrow()

    async def execute_arrow_async(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pa.Table:
        return self.execute_arrow(query, params)

    def export(
        self,
        query: str,
        format: ColumnarExportFormat = "parquet",
        params: Sequence[Any] | dict[str, Any] | None = None,
        compression: str = "zstd",
    ) -> ColumnarExportResult:
        df = self.execute_polars(query, params)
        meta = ColumnarProjectionMetadata(
            num_rows=df.height,
            num_columns=df.width,
            column_names=tuple(df.columns),
            byte_size=100,
        )
        return ColumnarExportResult(
            data=b"dummy-binary",
            format=format,
            metadata=meta,
        )

    async def export_async(
        self,
        query: str,
        format: ColumnarExportFormat = "parquet",
        params: Sequence[Any] | dict[str, Any] | None = None,
        compression: str = "zstd",
    ) -> ColumnarExportResult:
        return self.export(query, format, params, compression)


async def test_dummy_polars_projection_port():
    port = DummyPolarsProjectionPort()

    df = port.execute_polars("SELECT * FROM items")
    assert df.height == 2
    assert df.columns == ["id", "name"]

    df_async = await port.execute_polars_async("SELECT * FROM items")
    assert df_async.height == 2

    table = port.execute_arrow("SELECT * FROM items")
    assert table.num_rows == 2

    table_async = await port.execute_arrow_async("SELECT * FROM items")
    assert table_async.num_rows == 2

    exported = port.export("SELECT * FROM items", format="parquet")
    assert exported.data == b"dummy-binary"
    assert exported.format == "parquet"
    assert exported.metadata.num_rows == 2

    exported_async = await port.export_async("SELECT * FROM items", format="json")
    assert exported_async.format == "json"


def test_polars_projection_port_is_abstract() -> None:
    """Verify that PolarsProjectionPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(PolarsProjectionPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        PolarsProjectionPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_polars_projection_port_abstract_methods() -> None:
    """Verify abstract methods on PolarsProjectionPort."""
    expected = {
        "execute_arrow",
        "execute_arrow_async",
        "execute_polars",
        "execute_polars_async",
        "export",
        "export_async",
    }
    abstracts = PolarsProjectionPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
