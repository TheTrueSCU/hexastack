"""Hexagonal architecture boundary tests for hexastack_db."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_db_clean_architecture():
    """Assert hexastack_db strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_db")
