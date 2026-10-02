"""Hexagonal architecture boundary tests for hexastack."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_clean_architecture():
    """Assert hexastack strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack")
