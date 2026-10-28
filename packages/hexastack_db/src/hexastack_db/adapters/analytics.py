"""Concrete Polars and Apache Arrow columnar query projection adapter.

Notes/Architectural Intent:
    Implements PolarsProjectionPort over SQLAlchemy engines, raw connections,
    connectorx zero-copy database streaming, and embedded DuckDB repositories.
    Provides vectorized in-memory query projection and high-speed export formats.
"""

from __future__ import annotations

import asyncio
import io
import time
from typing import TYPE_CHECKING, Any, cast

from hexastack_core.utils import require_dependency
from hexastack_db.domain.analytics import (
    ColumnarExportFormat,
    ColumnarExportResult,
    ColumnarProjectionMetadata,
)
from hexastack_db.domain.exceptions import ColumnarQueryError
from hexastack_db.ports.analytics import PolarsProjectionPort

if TYPE_CHECKING:
    from collections.abc import Sequence

    import polars as pl
    import pyarrow as pa


def _require_polars() -> Any:
    """Import and return the polars module or raise an informative ImportError."""
    return require_dependency(
        "polars",
        extra="analytics",
        package="hexastack-db",
        feature_name="PolarsColumnarAdapter",
    )


def _require_pyarrow() -> Any:
    """Import and return the pyarrow module or raise an informative ImportError."""
    return require_dependency(
        "pyarrow",
        extra="analytics",
        package="hexastack-db",
        feature_name="PolarsColumnarAdapter",
    )


class PolarsColumnarAdapter(PolarsProjectionPort):
    """High-throughput columnar projection adapter integrating Polars, Arrow, and ConnectorX.

    Notes/Architectural Intent:
        Executes analytical SQL read queries directly into vectorized Arrow tables
        and Polars DataFrames. Bypasses Python object instantiation and ORM overhead
        for high-volume CQRS query endpoints.
    """

    def __init__(
        self,
        engine_or_connection: Any | None = None,
        connection_uri: str | None = None,
        enable_connectorx: bool = True,
    ) -> None:
        """Initialize PolarsColumnarAdapter with database connection or URI.

        Args:
            engine_or_connection: SQLAlchemy Engine, Connection, or DuckDB repository/connection.
            connection_uri: Optional database connection string (e.g. 'sqlite:///data.db').
            enable_connectorx: Whether to attempt zero-copy Rust streaming via connectorx if available.
        """
        self.engine_or_connection = engine_or_connection
        self.connection_uri = connection_uri
        self.enable_connectorx = enable_connectorx

    def _execute_to_polars(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pl.DataFrame:
        """Internal synchronous projection to Polars DataFrame."""
        pl_mod = _require_polars()

        # 1. Check if DuckDB connection or DuckDbRepository
        duckdb_conn = getattr(self.engine_or_connection, "_conn", None) or getattr(
            self.engine_or_connection, "conn", None
        )
        if hasattr(self.engine_or_connection, "sql") and callable(
            self.engine_or_connection.sql
        ):
            duckdb_conn = self.engine_or_connection

        if duckdb_conn is not None and hasattr(duckdb_conn, "sql"):
            try:
                rel = duckdb_conn.sql(query, params=params)
                arrow_table = rel.arrow()
                return pl_mod.from_arrow(arrow_table)
            except Exception as exc:
                msg = f"DuckDB columnar projection failed: {exc}"
                raise ColumnarQueryError(msg, query=query) from exc

        # 2. Check if connectorx URI streaming is viable
        if self.enable_connectorx and self.connection_uri and params is None:
            try:
                import connectorx  # noqa: F401

                return pl_mod.read_database_uri(
                    query=query,
                    uri=self.connection_uri,
                    engine="connectorx",
                )
            except Exception:
                # Fall back gracefully to standard driver if connectorx cannot handle dialect
                pass

        # 3. Standard SQLAlchemy / database connection projection
        target = self.engine_or_connection or self.connection_uri
        if target is None:
            msg = "No database connection or connection URI provided to PolarsColumnarAdapter."
            raise ColumnarQueryError(msg, query=query)

        try:
            read_options: dict[str, Any] = {}
            if params is not None:
                read_options["execute_options"] = {"parameters": params}
            return pl_mod.read_database(
                query=query,
                connection=target,
                **read_options,
            )
        except Exception as exc:
            msg = f"Columnar projection failed: {exc}"
            raise ColumnarQueryError(msg, query=query) from exc

    def execute_polars(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pl.DataFrame:
        """Execute query directly into a Polars DataFrame.

        Args:
            query: SQL query string.
            params: Optional query parameters.

        Returns:
            A Polars DataFrame containing the query projection.
        """
        return self._execute_to_polars(query, params)

    async def execute_polars_async(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pl.DataFrame:
        """Asynchronously execute query into a Polars DataFrame.

        Args:
            query: SQL query string.
            params: Optional query parameters.

        Returns:
            A Polars DataFrame containing the query projection.
        """
        return await asyncio.to_thread(self.execute_polars, query, params)

    def execute_arrow(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pa.Table:
        """Execute query and stream results into an Apache Arrow Table.

        Args:
            query: SQL query string.
            params: Optional query parameters.

        Returns:
            An Apache Arrow Table.
        """
        _require_pyarrow()
        df = self.execute_polars(query, params)
        return df.to_arrow()

    async def execute_arrow_async(
        self,
        query: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> pa.Table:
        """Asynchronously execute query and stream results into an Apache Arrow Table.

        Args:
            query: SQL query string.
            params: Optional query parameters.

        Returns:
            An Apache Arrow Table.
        """
        return await asyncio.to_thread(self.execute_arrow, query, params)

    def export(
        self,
        query: str,
        format: ColumnarExportFormat = "parquet",
        params: Sequence[Any] | dict[str, Any] | None = None,
        compression: str = "zstd",
    ) -> ColumnarExportResult:
        """Execute query and serialize dataset directly to the specified format.

        Args:
            query: SQL query string.
            format: Target format ('parquet', 'arrow_ipc', 'json', 'csv').
            params: Optional query parameters.
            compression: Compression codec for Parquet/IPC ('zstd', 'snappy', 'lz4', 'uncompressed').

        Returns:
            ColumnarExportResult containing serialized bytes and execution metadata.
        """
        start = time.perf_counter()
        df = self.execute_polars(query, params)

        buf = io.BytesIO()
        try:
            if format == "parquet":
                df.write_parquet(buf, compression=cast("Any", compression))
                data = buf.getvalue()
            elif format == "arrow_ipc":
                ipc_comp = (
                    compression
                    if compression in ("uncompressed", "lz4", "zstd")
                    else "zstd"
                )
                df.write_ipc(buf, compression=cast("Any", ipc_comp))
                data = buf.getvalue()
            elif format == "json":
                data = df.write_json().encode("utf-8")
            elif format == "csv":
                data = df.write_csv().encode("utf-8")
            else:
                msg = f"Unsupported columnar export format: '{format}'"
                raise ColumnarQueryError(msg, query=query)
        except ColumnarQueryError:
            raise
        except Exception as exc:
            msg = f"Failed to serialize columnar dataset to {format}: {exc}"
            raise ColumnarQueryError(msg, query=query) from exc

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        meta = ColumnarProjectionMetadata(
            num_rows=df.height,
            num_columns=df.width,
            column_names=tuple(df.columns),
            byte_size=len(data),
            execution_time_ms=elapsed_ms,
        )
        return ColumnarExportResult(
            data=data,
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
        """Asynchronously execute query and serialize to the specified format.

        Args:
            query: SQL query string.
            format: Target format ('parquet', 'arrow_ipc', 'json', 'csv').
            params: Optional query parameters.
            compression: Compression codec for Parquet/IPC.

        Returns:
            ColumnarExportResult containing serialized bytes and execution metadata.
        """
        return await asyncio.to_thread(self.export, query, format, params, compression)


__all__ = [
    "PolarsColumnarAdapter",
]
