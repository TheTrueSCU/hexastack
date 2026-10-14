"""Unit tests for hexastack_core.exceptions."""

from __future__ import annotations

import pytest

from hexastack_core.exceptions import (
    HexastackError,
    MissingDependencyError,
)


def test_hexastack_error_base() -> None:
    """Verify HexastackError is a standard Exception subclass."""
    err = HexastackError("root framework failure")
    assert isinstance(err, Exception)
    assert str(err) == "root framework failure"


def test_missing_dependency_error_hierarchy() -> None:
    """Verify MissingDependencyError dual-inherits from ImportError and HexastackError."""
    err = MissingDependencyError("Missing optional library 'redis'")
    assert isinstance(err, ImportError)
    assert isinstance(err, HexastackError)
    assert isinstance(err, Exception)
    assert str(err) == "Missing optional library 'redis'"


def test_missing_dependency_error_catchable_as_import_error() -> None:
    """Verify MissingDependencyError can be caught by standard ImportError handlers."""
    with pytest.raises(ImportError) as exc_info:
        raise MissingDependencyError("Testing ImportError catchability")
    assert isinstance(exc_info.value, HexastackError)
