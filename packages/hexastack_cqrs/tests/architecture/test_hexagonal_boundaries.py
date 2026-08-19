"""Hexagonal architecture boundary tests for hexastack_cqrs."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_cqrs_clean_architecture():
    """Assert hexastack_cqrs strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_cqrs")
