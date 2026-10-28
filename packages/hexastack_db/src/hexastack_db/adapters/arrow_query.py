"""CQRS read-model query handler for zero-copy Arrow and Polars projections.

Notes/Architectural Intent:
    Provides a standardized CQRS query handler abstraction that produces Apache Arrow
    tables and Polars DataFrames directly from analytical read queries, eliminating
    ORM object hydration overhead in high-throughput query pipelines.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hexastack_db.adapters.analytics import PolarsColumnarAdapter
from hexastack_db.ports.analytics import PolarsProjectionPort

if TYPE_CHECKING:
    from collections.abc import Sequence

    import polars as pl
    import pyarrow as pa

    from hexastack_db.domain.analytics import (
        ColumnarExportFormat,
        ColumnarExportResult,
    )


class ArrowQueryHandler:
    """CQRS query dispatcher executing zero-copy analytical columnar projections.

    Notes/Architectural Intent:
        Dispatches read queries through a PolarsProjectionPort adapter to stream
        vectorized Arrow tables, Polars DataFrames, or serialized binary exports.
    """

    def __init__(
        self,
        adapter: PolarsProjectionPort | None = None,
        engine_or_connection: Any | None = None,
        connection_uri: str | None = None,
    ) -> None:
        """Initialize ArrowQueryHandler.

        Args:
            adapter: Optional pre-configured PolarsProjectionPort instance.
            engine_or_connection: Optional database engine, connection, or DuckDB repository.
            connection_uri: Optional database connection string.
        """
        if adapter is not None:
            self.adapter = adapter
        else:
            self.adapter = PolarsColumnarAdapter(
                engine_or_connection=engine_or_connection,
                connection_uri=connection_uri,
            )

    def query_arrow(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pa.Table:
        """Execute query and return an Apache Arrow Table.

        Args:
            query: SQL query string.
            params: Optional query parameters.

        Returns:
            Apache Arrow Table.
        """
        return self.adapter.execute_arrow(query, params)

    async def query_arrow_async(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pa.Table:
        """Asynchronously execute query and return an Apache Arrow Table.

        Args:
            query: SQL query string.
            params: Optional query parameters.

        Returns:
            Apache Arrow Table.
        """
        return await self.adapter.execute_arrow_async(query, params)

    def query_polars(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pl.DataFrame:
        """Execute query and return a Polars DataFrame.

        Args:
            query: SQL query string.
            params: Optional query parameters.

        Returns:
            Polars DataFrame.
        """
        return self.adapter.execute_polars(query, params)

    async def query_polars_async(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pl.DataFrame:
        """Asynchronously execute query and return a Polars DataFrame.

        Args:
            query: SQL query string.
            params: Optional query parameters.

        Returns:
            Polars DataFrame.
        """
        return await self.adapter.execute_polars_async(query, params)

    def query_export(
        self,
        query: str,
        format: ColumnarExportFormat = "parquet",
        params: Sequence[Any] | dict[str, Any] | None = None,
        compression: str = "zstd",
    ) -> ColumnarExportResult:
        """Execute query and serialize dataset directly to target format.

        Args:
            query: SQL query string.
            format: Target format ('parquet', 'arrow_ipc', 'json', 'csv').
            params: Optional query parameters.
            compression: Compression codec for Parquet/IPC.

        Returns:
            ColumnarExportResult containing serialized payload and metadata.
        """
        return self.adapter.export(
            query, format=format, params=params, compression=compression
        )

    async def query_export_async(
        self,
        query: str,
        format: ColumnarExportFormat = "parquet",
        params: Sequence[Any] | dict[str, Any] | None = None,
        compression: str = "zstd",
    ) -> ColumnarExportResult:
        """Asynchronously execute query and serialize dataset to target format.

        Args:
            query: SQL query string.
            format: Target format ('parquet', 'arrow_ipc', 'json', 'csv').
            params: Optional query parameters.
            compression: Compression codec for Parquet/IPC.

        Returns:
            ColumnarExportResult containing serialized payload and metadata.
        """
        return await self.adapter.export_async(
            query, format=format, params=params, compression=compression
        )


__all__ = [
    "ArrowQueryHandler",
]
