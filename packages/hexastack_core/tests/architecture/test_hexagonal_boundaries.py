"""Hexagonal architecture boundary tests for hexastack_core."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_core_clean_architecture():
    """Assert hexastack_core strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_core")
