"""Hexagonal architecture boundary tests for hexastack_flow."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_flow_clean_architecture():
    """Assert hexastack_flow strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_flow")
