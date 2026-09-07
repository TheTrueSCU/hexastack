"""In-process embedded DuckDB OLAP analytics repository adapter.

Notes/Architectural Intent:
    Provides embedded high-throughput vectorized SQL analytics, Parquet/Arrow file querying,
    and CQRS analytical read projection execution without requiring external database servers.
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import inspect
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypeVar, cast

from hexastack_core.ports.repository import (
    AsyncRepositoryPort,
    RepositoryPort,
)
from hexastack_db.domain.exceptions import (
    DatabaseConnectionError,
    DatabaseError,
    UniqueConstraintViolationError,
)

T = TypeVar("T")
ID = TypeVar("ID")


def _require_duckdb() -> Any:
    """Import and return the duckdb module or raise an informative ImportError.

    Returns:
        The imported duckdb module.

    Raises:
        ImportError: If duckdb is not installed in the active environment.
    """
    try:
        import duckdb

        return duckdb
    except ImportError as exc:
        raise ImportError(
            "duckdb is required for DuckDbRepository. "
            "Install with: pip install hexastack-db[duckdb]"
        ) from exc


def _py_type_to_duckdb(py_type: Any) -> str:
    """Map python type annotation to DuckDB SQL column type."""
    if py_type is int:
        return "BIGINT"
    if py_type is float:
        return "DOUBLE"
    if py_type is bool:
        return "BOOLEAN"
    if py_type is str:
        return "VARCHAR"
    if py_type is bytes:
        return "BLOB"
    origin = getattr(py_type, "__origin__", None)
    if origin in (list, dict, set) or py_type in (list, dict, set):
        return "JSON"
    return "VARCHAR"


class DuckDbRepository[T, ID](RepositoryPort[T, ID]):
    """Embedded DuckDB OLAP repository adapter for high-speed columnar and analytical queries.

    Notes/Architectural Intent:
        Implements RepositoryPort over an embedded in-memory or file-backed DuckDB engine.
        Supports fast vectorized aggregation, zero-copy Arrow/Polars/Pandas export, and
        direct Parquet/SQLite external querying for CQRS read projections.
    """

    def __init__(
        self,
        database: str | Path | Any = ":memory:",
        *,
        read_only: bool = False,
        config: dict[str, Any] | None = None,
        model_cls: type[T] | None = None,
        table_name: str | None = None,
        id_column: str = "id",
        auto_create_table: bool = True,
    ) -> None:
        """Initialize DuckDbRepository with connection target and configuration.

        Args:
            database: Path to DuckDB file, ':memory:', or existing DuckDBPyConnection.
            read_only: Whether to open file-backed database in read-only mode.
            config: Optional DuckDB configuration dictionary.
            model_cls: Optional model or entity class (dataclass, Pydantic, or dict).
            table_name: Optional explicit table name. Defaults to lowercase model name.
            id_column: Name of the unique identifier column (default: 'id').
            auto_create_table: Whether to automatically create table if absent.
        """
        duckdb_mod = _require_duckdb()

        self._db_target = database
        self._read_only = read_only
        self._config = config or {}
        self._model_cls = model_cls
        self._id_column = id_column
        self._lock = threading.RLock()
        self._conn: Any = None

        if table_name:
            self._table_name = table_name
        elif model_cls is not None:
            self._table_name = model_cls.__name__.lower()
        else:
            self._table_name = "entities"

        try:
            if isinstance(database, duckdb_mod.DuckDBPyConnection):
                self._conn = database
            else:
                db_str = str(database) if isinstance(database, Path) else str(database)
                self._conn = duckdb_mod.connect(
                    database=db_str,
                    read_only=read_only,
                    config=self._config,
                )
        except Exception as exc:
            raise DatabaseConnectionError(
                f"Failed to connect to DuckDB at '{database}': {exc}"
            ) from exc

        if auto_create_table and not read_only:
            self._ensure_table()

    @property
    def connection(self) -> Any:
        """Return the underlying active DuckDB connection instance."""
        return self._conn

    @property
    def _active_conn(self) -> Any:
        """Return non-null active connection instance."""
        conn = self._conn
        if conn is None:
            raise DatabaseError(
                f"DuckDbRepository for table '{self._table_name}' is closed."
            )
        return conn

    @property
    def table_name(self) -> str:
        """Return the target table name managed by this repository."""
        return self._table_name

    def _ensure_table(self) -> None:
        """Create target table if it does not already exist."""
        with self._lock:
            if self._model_cls is not None and hasattr(
                self._model_cls, "__annotations__"
            ):
                columns: list[str] = []
                for name, field_type in self._model_cls.__annotations__.items():
                    sql_type = _py_type_to_duckdb(field_type)
                    if name == self._id_column:
                        columns.append(f"{name} {sql_type} PRIMARY KEY")
                    else:
                        columns.append(f"{name} {sql_type}")
                col_defs = ", ".join(columns)
                ddl = f"CREATE TABLE IF NOT EXISTS {self._table_name} ({col_defs})"
            else:
                ddl = (
                    f"CREATE TABLE IF NOT EXISTS {self._table_name} "
                    f"({self._id_column} VARCHAR PRIMARY KEY, data JSON)"
                )
            try:
                self._active_conn.execute(ddl)
            except Exception as exc:
                raise DatabaseError(
                    f"Failed to ensure table '{self._table_name}': {exc}"
                ) from exc

    def _entity_to_dict(self, entity: Any) -> dict[str, Any]:
        """Serialize entity instance to dictionary mapping."""
        if hasattr(entity, "model_dump"):
            dump_fn = entity.model_dump
            return cast("dict[str, Any]", dump_fn())
        if dataclasses.is_dataclass(entity) and not isinstance(entity, type):
            return dataclasses.asdict(entity)
        if isinstance(entity, dict):
            return entity
        if hasattr(entity, "__dict__"):
            return cast("dict[str, Any]", entity.__dict__)
        raise ValueError(f"Unsupported entity type '{type(entity)}' for serialization.")

    def _dict_to_entity(self, row: dict[str, Any]) -> T:
        """Convert row dictionary into domain entity instance."""
        if self._model_cls is None:
            return cast("T", row)
        if hasattr(self._model_cls, "model_validate"):
            validate_fn: Any = self._model_cls.model_validate
            return cast("T", validate_fn(row))
        if dataclasses.is_dataclass(self._model_cls) or inspect.isclass(
            self._model_cls
        ):
            cls_target: Any = self._model_cls
            return cast("T", cls_target(**row))
        return cast("T", row)

    def add(self, entity: T) -> None:
        """Persist a new entity to the DuckDB table.

        Args:
            entity: Domain entity instance to insert.

        Raises:
            UniqueConstraintViolationError: If an entity with the same ID exists.
            DatabaseError: If database persistence fails.
        """
        row = self._entity_to_dict(entity)
        keys = list(row.keys())
        placeholders = ", ".join(["?"] * len(keys))
        columns = ", ".join(keys)
        values = [row[k] for k in keys]

        sql = f"INSERT INTO {self._table_name} ({columns}) VALUES ({placeholders})"  # noqa: S608
        with self._lock:
            try:
                self._active_conn.execute(sql, values)
            except Exception as exc:
                msg = str(exc)
                if (
                    "Constraint Error" in msg
                    or "PRIMARY KEY" in msg
                    or "Duplicate" in msg
                ):
                    raise UniqueConstraintViolationError(
                        f"Unique constraint violation inserting into '{self._table_name}': {exc}"
                    ) from exc
                raise DatabaseError(
                    f"Failed to insert into '{self._table_name}': {exc}"
                ) from exc

    def add_many(self, entities: Sequence[T]) -> None:
        """Persist multiple entities in batch.

        Args:
            entities: Sequence of entity instances to insert.

        Raises:
            DatabaseError: If batch insertion fails.
        """
        if not entities:
            return
        rows = [self._entity_to_dict(e) for e in entities]
        keys = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(keys))
        columns = ", ".join(keys)
        sql = f"INSERT INTO {self._table_name} ({columns}) VALUES ({placeholders})"  # noqa: S608

        values_list = [[r[k] for k in keys] for r in rows]
        with self._lock:
            try:
                self._active_conn.executemany(sql, values_list)
            except Exception as exc:
                msg = str(exc)
                if (
                    "Constraint Error" in msg
                    or "PRIMARY KEY" in msg
                    or "Duplicate" in msg
                ):
                    raise UniqueConstraintViolationError(
                        f"Unique constraint violation during batch insert: {exc}"
                    ) from exc
                raise DatabaseError(
                    f"Failed to batch insert into '{self._table_name}': {exc}"
                ) from exc

    def get_by_id(self, entity_id: ID) -> T | None:
        """Retrieve an entity instance by its primary identifier.

        Args:
            entity_id: The unique identifier.

        Returns:
            The entity instance if found, None otherwise.
        """
        sql = f"SELECT * FROM {self._table_name} WHERE {self._id_column} = ? LIMIT 1"  # noqa: S608
        with self._lock:
            try:
                cursor = self._active_conn.execute(sql, [entity_id])
                description = cursor.description
                if not description:
                    return None
                col_names = [col[0] for col in description]
                row = cursor.fetchone()
                if row is None:
                    return None
                row_dict = dict(zip(col_names, row, strict=False))
                return self._dict_to_entity(row_dict)
            except Exception as exc:
                raise DatabaseError(
                    f"Failed to query entity by ID '{entity_id}': {exc}"
                ) from exc

    def remove(self, entity_id: ID) -> None:
        """Remove an entity instance by its unique identifier.

        Args:
            entity_id: The unique identifier of entity to delete.

        Raises:
            DatabaseError: If deletion fails.
        """
        sql = f"DELETE FROM {self._table_name} WHERE {self._id_column} = ?"  # noqa: S608
        with self._lock:
            try:
                self._active_conn.execute(sql, [entity_id])
            except Exception as exc:
                raise DatabaseError(
                    f"Failed to delete entity with ID '{entity_id}': {exc}"
                ) from exc

    def list_all(self, limit: int | None = None, offset: int = 0) -> list[T]:
        """List all entities with optional pagination limit and offset.

        Args:
            limit: Optional maximum number of records to return.
            offset: Number of initial records to skip.

        Returns:
            List of domain entity instances.
        """
        sql = f"SELECT * FROM {self._table_name} OFFSET {offset}"  # noqa: S608
        if limit is not None:
            sql = f"SELECT * FROM {self._table_name} LIMIT {limit} OFFSET {offset}"  # noqa: S608

        with self._lock:
            try:
                cursor = self._active_conn.execute(sql)
                col_names = [col[0] for col in (cursor.description or [])]
                rows = cursor.fetchall()
                return [
                    self._dict_to_entity(dict(zip(col_names, row, strict=False)))
                    for row in rows
                ]
            except Exception as exc:
                raise DatabaseError(
                    f"Failed to list all entities from '{self._table_name}': {exc}"
                ) from exc

    def count(self) -> int:
        """Return the total number of records in the target table."""
        sql = f"SELECT count(*) FROM {self._table_name}"  # noqa: S608
        res = self.query_scalar(sql)
        return int(res) if res is not None else 0

    def query(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a raw SQL query and return rows as dictionaries.

        Args:
            sql: SQL statement to execute.
            params: Optional parameters for query placeholder substitution.

        Returns:
            List of row dictionaries.

        Raises:
            DatabaseError: If SQL execution fails.
        """
        with self._lock:
            try:
                cursor = (
                    self._active_conn.execute(sql, params)
                    if params
                    else self._active_conn.execute(sql)
                )
                col_names = [col[0] for col in (cursor.description or [])]
                rows = cursor.fetchall()
                return [dict(zip(col_names, row, strict=False)) for row in rows]
            except Exception as exc:
                raise DatabaseError(f"Query execution failed: {exc}") from exc

    def query_entities(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> list[T]:
        """Execute an analytical query mapping result rows to entity models."""
        rows = self.query(sql, params)
        return [self._dict_to_entity(r) for r in rows]

    def query_scalar(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> Any:
        """Execute a query and return the first column of the first row.

        Args:
            sql: SQL query returning a single scalar value.
            params: Optional query parameters.

        Returns:
            The scalar value, or None if the result set is empty.
        """
        with self._lock:
            try:
                cursor = (
                    self._active_conn.execute(sql, params)
                    if params
                    else self._active_conn.execute(sql)
                )
                row = cursor.fetchone()
                return row[0] if row else None
            except Exception as exc:
                raise DatabaseError(f"Scalar query execution failed: {exc}") from exc

    def query_df(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> Any:
        """Execute an analytical query returning a Pandas DataFrame.

        Args:
            sql: SQL query statement.
            params: Optional query parameters.

        Returns:
            pandas.DataFrame containing query results.
        """
        with self._lock:
            try:
                rel = (
                    self._active_conn.sql(sql, params=params)
                    if params
                    else self._active_conn.sql(sql)
                )
                return rel.df()
            except Exception as exc:
                raise DatabaseError(f"DataFrame query execution failed: {exc}") from exc

    def query_arrow(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> Any:
        """Execute an analytical query returning a PyArrow Table (zero-copy).

        Args:
            sql: SQL query statement.
            params: Optional query parameters.

        Returns:
            pyarrow.Table containing query results.
        """
        with self._lock:
            try:
                rel = (
                    self._active_conn.sql(sql, params=params)
                    if params
                    else self._active_conn.sql(sql)
                )
                arrow_res = rel.arrow()
                if hasattr(arrow_res, "read_all"):
                    return arrow_res.read_all()
                return arrow_res
            except Exception as exc:
                raise DatabaseError(f"Arrow query execution failed: {exc}") from exc

    def query_polars(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> Any:
        """Execute an analytical query returning a Polars DataFrame.

        Args:
            sql: SQL query statement.
            params: Optional query parameters.

        Returns:
            polars.DataFrame containing query results.
        """
        with self._lock:
            try:
                rel = (
                    self._active_conn.sql(sql, params=params)
                    if params
                    else self._active_conn.sql(sql)
                )
                return rel.pl()
            except Exception as exc:
                raise DatabaseError(f"Polars query execution failed: {exc}") from exc

    def execute(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> None:
        """Execute an arbitrary DDL or DML statement."""
        with self._lock:
            try:
                if params:
                    self._active_conn.execute(sql, params)
                else:
                    self._active_conn.execute(sql)
            except Exception as exc:
                raise DatabaseError(f"Execute statement failed: {exc}") from exc

    def register_view(self, view_name: str, query_or_df: Any) -> None:
        """Register a view or Python object (DataFrame/Relation) under a table name.

        Args:
            view_name: Name of the virtual view/table to create.
            query_or_df: SQL query string, Pandas/Polars DataFrame, or PyArrow Table.
        """
        with self._lock:
            try:
                if isinstance(query_or_df, str):
                    self._active_conn.execute(
                        f"CREATE OR REPLACE VIEW {view_name} AS {query_or_df}"
                    )
                else:
                    self._active_conn.register(view_name, query_or_df)
            except Exception as exc:
                raise DatabaseError(
                    f"Failed to register view '{view_name}': {exc}"
                ) from exc

    def register_parquet(self, view_name: str, file_path_or_glob: str | Path) -> None:
        """Register a virtual view backed by one or more Parquet files.

        Args:
            view_name: View name to register.
            file_path_or_glob: Path or glob string to Parquet file(s).
        """
        path_str = str(file_path_or_glob)
        sql = f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_parquet('{path_str}')"  # noqa: S608
        self.execute(sql)

    def attach_sqlite(
        self, sqlite_path: str | Path, schema_name: str = "sqlite_db"
    ) -> None:
        """Attach an existing SQLite database file directly into DuckDB.

        Args:
            sqlite_path: Path to the SQLite database file.
            schema_name: Virtual schema identifier to mount (default: 'sqlite_db').
        """
        path_str = str(sqlite_path)
        sql = f"ATTACH '{path_str}' AS {schema_name} (TYPE SQLITE)"
        self.execute(sql)

    def export_parquet(
        self,
        table_or_query: str,
        output_path: str | Path,
        compression: str = "zstd",
    ) -> None:
        """Export table or query result to a Parquet file.

        Args:
            table_or_query: Table name or SELECT query.
            output_path: Target Parquet file destination path.
            compression: Compression codec (e.g. 'zstd', 'snappy', 'gzip').
        """
        out_str = str(output_path)
        source = (
            table_or_query
            if table_or_query.strip().upper().startswith("SELECT")
            else f"SELECT * FROM {table_or_query}"  # noqa: S608
        )
        sql = f"COPY ({source}) TO '{out_str}' (FORMAT PARQUET, COMPRESSION '{compression}')"
        self.execute(sql)

    def export_csv(self, table_or_query: str, output_path: str | Path) -> None:
        """Export table or query result to a CSV file."""
        out_str = str(output_path)
        source = (
            table_or_query
            if table_or_query.strip().upper().startswith("SELECT")
            else f"SELECT * FROM {table_or_query}"  # noqa: S608
        )
        sql = f"COPY ({source}) TO '{out_str}' (FORMAT CSV, HEADER)"
        self.execute(sql)

    def close(self) -> None:
        """Close the DuckDB connection and free native resources."""
        with self._lock:
            if hasattr(self, "_conn") and self._conn is not None:
                with contextlib.suppress(Exception):
                    self._conn.close()
                self._conn = None

    def __enter__(self) -> DuckDbRepository[T, ID]:
        """Enter synchronous runtime context."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit synchronous runtime context."""
        self.close()


class AsyncDuckDbRepository[T, ID](AsyncRepositoryPort[T, ID]):
    """Asynchronous wrapper for DuckDbRepository running operations on threadpool.

    Notes/Architectural Intent:
        Wraps DuckDbRepository to satisfy AsyncRepositoryPort, ensuring analytical
        DuckDB queries do not block the active asyncio event loop.
    """

    def __init__(
        self,
        database: str | Path | Any = ":memory:",
        *,
        read_only: bool = False,
        config: dict[str, Any] | None = None,
        model_cls: type[T] | None = None,
        table_name: str | None = None,
        id_column: str = "id",
        auto_create_table: bool = True,
    ) -> None:
        """Initialize AsyncDuckDbRepository with target configuration."""
        self._sync_repo = DuckDbRepository[T, ID](
            database=database,
            read_only=read_only,
            config=config,
            model_cls=model_cls,
            table_name=table_name,
            id_column=id_column,
            auto_create_table=auto_create_table,
        )

    @property
    def sync_repo(self) -> DuckDbRepository[T, ID]:
        """Return the underlying synchronous DuckDbRepository instance."""
        return self._sync_repo

    async def add_async(self, entity: T) -> None:
        """Asynchronously insert an entity into DuckDB."""
        await asyncio.to_thread(self._sync_repo.add, entity)

    async def add_many_async(self, entities: Sequence[T]) -> None:
        """Asynchronously insert multiple entities in batch."""
        await asyncio.to_thread(self._sync_repo.add_many, entities)

    async def get_by_id_async(self, entity_id: ID) -> T | None:
        """Asynchronously fetch an entity by primary ID."""
        return await asyncio.to_thread(self._sync_repo.get_by_id, entity_id)

    async def remove_async(self, entity_id: ID) -> None:
        """Asynchronously delete an entity by primary ID."""
        await asyncio.to_thread(self._sync_repo.remove, entity_id)

    async def list_all_async(
        self, limit: int | None = None, offset: int = 0
    ) -> list[T]:
        """Asynchronously list all entities with pagination."""
        return await asyncio.to_thread(self._sync_repo.list_all, limit, offset)

    async def count_async(self) -> int:
        """Asynchronously return the total record count."""
        return await asyncio.to_thread(self._sync_repo.count)

    async def query_async(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Asynchronously execute raw SQL and return row dictionaries."""
        return await asyncio.to_thread(self._sync_repo.query, sql, params)

    async def query_entities_async(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> list[T]:
        """Asynchronously execute query mapping result rows to entity instances."""
        return await asyncio.to_thread(self._sync_repo.query_entities, sql, params)

    async def query_scalar_async(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> Any:
        """Asynchronously query a single scalar value."""
        return await asyncio.to_thread(self._sync_repo.query_scalar, sql, params)

    async def query_df_async(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> Any:
        """Asynchronously execute query returning a Pandas DataFrame."""
        return await asyncio.to_thread(self._sync_repo.query_df, sql, params)

    async def query_arrow_async(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> Any:
        """Asynchronously execute query returning a PyArrow Table."""
        return await asyncio.to_thread(self._sync_repo.query_arrow, sql, params)

    async def query_polars_async(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> Any:
        """Asynchronously execute query returning a Polars DataFrame."""
        return await asyncio.to_thread(self._sync_repo.query_polars, sql, params)

    async def execute_async(
        self,
        sql: str,
        params: Sequence[Any] | dict[str, Any] | None = None,
    ) -> None:
        """Asynchronously execute DDL or DML statement."""
        await asyncio.to_thread(self._sync_repo.execute, sql, params)

    async def register_view_async(self, view_name: str, query_or_df: Any) -> None:
        """Asynchronously register a virtual view or DataFrame."""
        await asyncio.to_thread(self._sync_repo.register_view, view_name, query_or_df)

    async def register_parquet_async(
        self, view_name: str, file_path_or_glob: str | Path
    ) -> None:
        """Asynchronously register a Parquet-backed virtual view."""
        await asyncio.to_thread(
            self._sync_repo.register_parquet, view_name, file_path_or_glob
        )

    async def export_parquet_async(
        self,
        table_or_query: str,
        output_path: str | Path,
        compression: str = "zstd",
    ) -> None:
        """Asynchronously export table or query to Parquet."""
        await asyncio.to_thread(
            self._sync_repo.export_parquet, table_or_query, output_path, compression
        )

    async def close_async(self) -> None:
        """Asynchronously close the DuckDB connection."""
        await asyncio.to_thread(self._sync_repo.close)

    async def __aenter__(self) -> AsyncDuckDbRepository[T, ID]:
        """Enter asynchronous runtime context."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit asynchronous runtime context."""
        await self.close_async()


__all__ = [
    "AsyncDuckDbRepository",
    "DuckDbRepository",
]
