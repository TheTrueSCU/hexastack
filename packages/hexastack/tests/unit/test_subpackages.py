"""Unit tests for subpackage discovery and registration utilities.

Notes/Architectural Intent:
    Ensures robust handling of subpackage discovery, namespace registration,
    directory listing, and clear error guidance for uninstalled extras.
"""

from unittest.mock import MagicMock, patch

import pytest

from hexastack.subpackages import (
    ALL_SUBPACKAGES,
    discover_and_register_subpackages,
    get_subpackage_dir,
    handle_missing_subpackage,
)


def test_discover_and_register_subpackages_success():
    """Verify subpackages are successfully discovered and registered in namespace."""
    target_globals: dict[str, object] = {}
    mock_module = MagicMock()

    with (
        patch("importlib.util.find_spec", return_value=MagicMock()),
        patch("importlib.import_module", return_value=mock_module),
    ):
        installed = discover_and_register_subpackages(target_globals, ["core", "cqrs"])

        installed_count = len(installed)
        assert installed_count == 2
        assert "core" in installed
        assert "cqrs" in installed

        core_bound = target_globals.get("core")
        assert core_bound is mock_module


def test_discover_and_register_subpackages_not_found_or_error():
    """Verify missing or failing subpackages are safely skipped."""
    target_globals: dict[str, object] = {}

    with (
        patch("importlib.util.find_spec", side_effect=[None, MagicMock()]),
        patch("importlib.import_module", side_effect=ImportError("broken dependency")),
    ):
        installed = discover_and_register_subpackages(
            target_globals, ["missing", "broken"]
        )

        installed_count = len(installed)
        assert installed_count == 0
        missing_in_globals = "missing" in target_globals
        assert missing_in_globals is False
        broken_in_globals = "broken" in target_globals
        assert broken_in_globals is False


def test_get_subpackage_dir():
    """Verify get_subpackage_dir merges globals and installed shorthands."""
    test_globals = {"existing_var": 1, "__name__": "hexastack"}
    installed = ["core", "cqrs"]

    result = get_subpackage_dir(test_globals, installed)

    assert "core" in result
    assert "cqrs" in result
    assert "existing_var" in result
    assert "__name__" in result
    is_sorted = result == sorted(result)
    assert is_sorted is True


def test_handle_missing_subpackage_known_shorthand():
    """Verify known uninstalled subpackage raises AttributeError with guidance."""
    with pytest.raises(AttributeError) as exc_info:
        handle_missing_subpackage("ai", ALL_SUBPACKAGES)

    error_msg = str(exc_info.value)
    assert "Package 'hexastack-ai' is not installed" in error_msg
    assert "pip install hexastack[ai]" in error_msg


def test_handle_missing_subpackage_unknown_attribute():
    """Verify unknown attribute raises standard AttributeError."""
    with pytest.raises(AttributeError) as exc_info:
        handle_missing_subpackage("completely_random_symbol", ALL_SUBPACKAGES)

    error_msg = str(exc_info.value)
    assert "module 'hexastack' has no attribute 'completely_random_symbol'" in error_msg
