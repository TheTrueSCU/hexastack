"""Hexagonal architecture boundary tests for hexastack_mcp."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_mcp_clean_architecture():
    """Assert hexastack_mcp strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_mcp")
