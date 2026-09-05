"""Hexagonal architecture boundary tests for hexastack_tools."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_tools_clean_architecture():
    """Assert hexastack_tools strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_tools")
