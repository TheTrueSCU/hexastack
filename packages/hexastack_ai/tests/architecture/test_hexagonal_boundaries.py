"""Hexagonal architecture boundary tests for hexastack_ai."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_ai_clean_architecture():
    """Assert hexastack_ai strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_ai")
