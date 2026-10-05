"""Hexagonal architecture boundary tests for hexastack_cli."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_cli_clean_architecture():
    """Assert hexastack_cli strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_cli")
