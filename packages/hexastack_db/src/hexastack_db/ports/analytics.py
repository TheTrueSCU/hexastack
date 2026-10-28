"""Abstract ports for zero-copy columnar query projections and analytical exports.

Notes/Architectural Intent:
    Defines the contract for executing high-throughput analytical queries directly
    into Polars DataFrames and Apache Arrow Tables, bypassing ORM object hydration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from hexastack_db.domain.analytics import (
    ColumnarExportFormat,
    ColumnarExportResult,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    import polars as pl
    import pyarrow as pa


class PolarsProjectionPort(ABC):
    """Abstract port for vectorized columnar query projection and instant export.

    Notes/Architectural Intent:
        Enables CQRS read models and OLAP workflows to stream zero-copy columnar
        record batches without serializing individual Python row objects.
    """

    @abstractmethod
    def execute_polars(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pl.DataFrame:
        """Execute a query and project results directly into a Polars DataFrame.

        Args:
            query: SQL query string to execute.
            params: Optional query parameters.

        Returns:
            A Polars DataFrame containing the query projection.

        Raises:
            ColumnarQueryError: If query execution or Arrow ingestion fails.
        """

    @abstractmethod
    async def execute_polars_async(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pl.DataFrame:
        """Asynchronously execute a query and project results into a Polars DataFrame.

        Args:
            query: SQL query string to execute.
            params: Optional query parameters.

        Returns:
            A Polars DataFrame containing the query projection.

        Raises:
            ColumnarQueryError: If query execution or Arrow ingestion fails.
        """

    @abstractmethod
    def execute_arrow(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pa.Table:
        """Execute a query and stream results into an Apache Arrow Table.

        Args:
            query: SQL query string to execute.
            params: Optional query parameters.

        Returns:
            An Apache Arrow Table.

        Raises:
            ColumnarQueryError: If query execution fails.
        """

    @abstractmethod
    async def execute_arrow_async(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pa.Table:
        """Asynchronously execute a query and stream results into an Apache Arrow Table.

        Args:
            query: SQL query string to execute.
            params: Optional query parameters.

        Returns:
            An Apache Arrow Table.

        Raises:
            ColumnarQueryError: If query execution fails.
        """

    @abstractmethod
    def export(
        self,
        query: str,
        format: ColumnarExportFormat = "parquet",
        params: Sequence[Any] | dict[str, Any] | None = None,
        compression: str = "zstd",
    ) -> ColumnarExportResult:
        """Execute a query and serialize the columnar dataset directly to the specified format.

        Args:
            query: SQL query string to execute.
            format: Target binary or text format ('parquet', 'arrow_ipc', 'json', 'csv').
            params: Optional query parameters.
            compression: Compression codec for Parquet/IPC ('zstd', 'snappy', 'lz4', 'uncompressed').

        Returns:
            ColumnarExportResult containing serialized bytes and execution metadata.

        Raises:
            ColumnarQueryError: If query execution or serialization fails.
        """

    @abstractmethod
    async def export_async(
        self,
        query: str,
        format: ColumnarExportFormat = "parquet",
        params: Sequence[Any] | dict[str, Any] | None = None,
        compression: str = "zstd",
    ) -> ColumnarExportResult:
        """Asynchronously execute a query and serialize the columnar dataset to the specified format.

        Args:
            query: SQL query string to execute.
            format: Target format ('parquet', 'arrow_ipc', 'json', 'csv').
            params: Optional query parameters.
            compression: Compression codec for Parquet/IPC.

        Returns:
            ColumnarExportResult containing serialized bytes and execution metadata.

        Raises:
            ColumnarQueryError: If query execution or serialization fails.
        """


__all__ = [
    "PolarsProjectionPort",
]
