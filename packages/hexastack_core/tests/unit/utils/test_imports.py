"""Unit tests for require_dependency utility."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from hexastack_core.utils.imports import require_dependency


def test_require_dependency_installed_module() -> None:
    """Test successful import of an installed module."""
    mod = require_dependency("json", extra="core", package="hexastack-core")
    assert mod is not None
    assert hasattr(mod, "dumps")


def test_require_dependency_missing_module() -> None:
    """Test that importing a missing module raises an informative ImportError."""
    with (
        patch(
            "importlib.import_module",
            side_effect=ImportError("No module named 'nonexistent_lib'"),
        ),
        pytest.raises(
            ImportError,
            match=r"Optional dependency 'nonexistent_lib' is required\. Install with: pip install hexastack-events\[dlt\]",
        ) as exc_info,
    ):
        require_dependency(
            "nonexistent_lib",
            extra="dlt",
            package="hexastack-events",
        )

    assert exc_info.value.__cause__ is not None


def test_require_dependency_missing_module_with_feature_name() -> None:
    """Test that feature_name is included in the error message when provided."""
    with (
        patch(
            "importlib.import_module",
            side_effect=ImportError("No module named 'fake_lib'"),
        ),
        pytest.raises(
            ImportError,
            match=r"Optional dependency 'fake_lib' is required for Kafka Event Bus\. Install with: pip install hexastack-events\[kafka\]",
        ),
    ):
        require_dependency(
            "fake_lib",
            extra="kafka",
            package="hexastack-events",
            feature_name="Kafka Event Bus",
        )
