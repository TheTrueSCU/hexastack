"""Filesystem utility functions for atomic, crash-consistent file operations.

Notes/Architectural Intent:
    Standard file writes truncate destination files in-place prior to writing new bytes.
    If a process terminates unexpectedly (crash, SIGKILL, power loss, disk quota), the target
    file is left in a corrupted or zero-byte state. Furthermore, concurrent file watchers or readers
    can observe partial, half-written payloads.

    This module implements the atomic replacement pattern: writing to an isolated temporary file
    in the target directory, flushing buffers to disk via `os.fsync`, and executing an atomic
    filesystem rename (`os.replace` / `Path.replace`). This guarantees that readers only ever
    observe completely written, consistent files.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Final

__all__ = ["atomic_write_bytes", "atomic_write_text"]

_DEFAULT_ENCODING: Final[str] = "utf-8"


def atomic_write_text(
    path: Path | str,
    content: str,
    encoding: str = _DEFAULT_ENCODING,
    mode: int | None = None,
) -> Path:
    """Atomically write text content to a file.

    Creates a temporary file in the target directory, writes the text payload,
    flushes buffers via fsync, and renames the temporary file over the destination.

    Args:
        path: Destination file path.
        content: Text content to write.
        encoding: Text encoding (defaults to utf-8).
        mode: Optional filesystem permissions (e.g. 0o644).

    Returns:
        Path object pointing to the written destination file.

    Raises:
        OSError: If filesystem operations fail.

    Notes/Architectural Intent:
        The temporary file is deliberately created within `path.parent` rather than
        the system temporary directory (`/tmp`) to guarantee both files reside on the
        same filesystem partition. Cross-filesystem renames fail or degrade to non-atomic
        copies.
    """
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=target.parent,
            prefix=f".{target.name}.tmp-",
            encoding=encoding,
            delete=False,
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(content)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        if mode is not None:
            tmp_path.chmod(mode)

        tmp_path.replace(target)
        return target
    except BaseException:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def atomic_write_bytes(
    path: Path | str,
    content: bytes,
    mode: int | None = None,
) -> Path:
    """Atomically write binary bytes content to a file.

    Creates a temporary file in the target directory, writes the byte payload,
    flushes buffers via fsync, and renames the temporary file over the destination.

    Args:
        path: Destination file path.
        content: Binary bytes to write.
        mode: Optional filesystem permissions (e.g. 0o600).

    Returns:
        Path object pointing to the written destination file.

    Raises:
        OSError: If filesystem operations fail.

    Notes/Architectural Intent:
        Guarantees that readers never observe partially written binary artifacts
        such as SQLite databases, compiled Protobuf descriptors, or encryption keys.
    """
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.tmp-",
            delete=False,
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(content)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        if mode is not None:
            tmp_path.chmod(mode)

        tmp_path.replace(target)
        return target
    except BaseException:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise
