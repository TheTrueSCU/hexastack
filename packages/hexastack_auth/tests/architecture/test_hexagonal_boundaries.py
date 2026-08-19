"""Hexagonal architecture boundary tests for hexastack_auth."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_auth_clean_architecture():
    """Assert hexastack_auth strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_auth")
