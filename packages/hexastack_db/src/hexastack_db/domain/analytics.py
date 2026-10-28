"""Domain models for columnar query projections and analytical exports.

Notes/Architectural Intent:
    Encapsulates immutable models representing columnar result metadata and exported
    binary payloads (Parquet, Arrow IPC, JSON, CSV) without coupling to specific
    database engines or network presentation transports.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ColumnarExportFormat = Literal["parquet", "arrow_ipc", "json", "csv"]


@dataclass(frozen=True)
class ColumnarProjectionMetadata:
    """Metadata describing a vectorized columnar query execution result.

    Notes/Architectural Intent:
        Captures row/column counts, column schemas, and execution timings
        for diagnostic observability and query budget governance.
    """

    num_rows: int
    num_columns: int
    column_names: tuple[str, ...]
    byte_size: int | None = None
    execution_time_ms: float | None = None


@dataclass(frozen=True)
class ColumnarExportResult:
    """Container holding serialized vectorized export bytes and metadata.

    Notes/Architectural Intent:
        Represents in-memory serialized columnar representations ready for instant
        streaming over HTTP, writing to object storage, or saving to disk.
    """

    data: bytes
    format: ColumnarExportFormat
    metadata: ColumnarProjectionMetadata

    def to_file(self, path: str | Path) -> Path:
        """Write the exported columnar binary payload to the filesystem.

        Args:
            path: Target file path destination.

        Returns:
            The Path where data was persisted.
        """
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.data)
        return target


__all__ = [
    "ColumnarExportFormat",
    "ColumnarExportResult",
    "ColumnarProjectionMetadata",
]
