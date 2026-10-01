"""Unit tests for atomic filesystem operations in hexastack_core.infra.fs.

Notes/Architectural Intent:
    Ensures atomic file writing utilities preserve crash-consistency invariants,
    guarantee proper permission application, cleanly unlink temporary files on exceptions,
    and never corrupt existing destination files.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from hexastack_core.infra.fs import atomic_write_bytes, atomic_write_text


def test_atomic_write_text_success(tmp_path: Path) -> None:
    """Verify writing text atomically produces the expected file content."""
    target_file = tmp_path / "hello.txt"
    content = "Hello, Hexastack!"

    res = atomic_write_text(target_file, content)

    target_exists = target_file.exists()
    assert target_exists is True
    res_matches = res == target_file
    assert res_matches is True
    read_text = target_file.read_text(encoding="utf-8")
    assert read_text == content


def test_atomic_write_text_creates_parent_directories(tmp_path: Path) -> None:
    """Verify missing parent directories are created automatically."""
    target_file = tmp_path / "nested" / "deep" / "config.toml"
    content = "[server]\nport = 8080\n"

    res = atomic_write_text(target_file, content)

    parent_exists = target_file.parent.exists()
    assert parent_exists is True
    file_exists = target_file.exists()
    assert file_exists is True
    read_content = target_file.read_text(encoding="utf-8")
    assert read_content == content
    assert res == target_file


def test_atomic_write_text_preserves_existing_file_on_write_failure(
    tmp_path: Path,
) -> None:
    """Verify destination file remains uncorrupted if an exception occurs mid-write."""
    target_file = tmp_path / "important.json"
    original_content = '{"status": "original"}'
    target_file.write_text(original_content, encoding="utf-8")

    with (
        patch("os.fsync", side_effect=OSError("Disk write simulated I/O error")),
        pytest.raises(OSError, match="Disk write simulated I/O error"),
    ):
        atomic_write_text(target_file, '{"status": "corrupted"}')

    # Original file must remain 100% intact
    current_content = target_file.read_text(encoding="utf-8")
    assert current_content == original_content

    # Ensure no leftover .tmp files in target directory
    tmp_files = list(tmp_path.glob(".*.tmp-*"))
    tmp_count = len(tmp_files)
    assert tmp_count == 0


def test_atomic_write_text_custom_mode(tmp_path: Path) -> None:
    """Verify permissions mode is applied to the written file."""
    target_file = tmp_path / "secret.env"
    content = "API_KEY=supersecret"

    atomic_write_text(target_file, content, mode=0o600)

    file_stat = target_file.stat()
    file_mode = file_stat.st_mode & 0o777
    assert file_mode == 0o600


def test_atomic_write_bytes_success(tmp_path: Path) -> None:
    """Verify binary bytes are written atomically."""
    target_file = tmp_path / "payload.bin"
    payload = b"\x00\x01\x02\x03\xff\xfe"

    res = atomic_write_bytes(target_file, payload, mode=0o644)

    file_exists = target_file.exists()
    assert file_exists is True
    read_bytes = target_file.read_bytes()
    assert read_bytes == payload
    assert res == target_file


def test_atomic_write_bytes_cleans_up_on_failure(tmp_path: Path) -> None:
    """Verify temporary files are cleaned up if byte writing fails."""
    target_file = tmp_path / "binary_crash.bin"

    with (
        patch("pathlib.Path.replace", side_effect=PermissionError("Access denied")),
        pytest.raises(PermissionError, match="Access denied"),
    ):
        atomic_write_bytes(target_file, b"data")

    file_exists = target_file.exists()
    assert file_exists is False
    tmp_files = list(tmp_path.glob(".*.tmp-*"))
    tmp_count = len(tmp_files)
    assert tmp_count == 0
