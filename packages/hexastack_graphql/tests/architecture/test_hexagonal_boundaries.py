"""Hexagonal architecture boundary tests for hexastack_graphql."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_graphql_clean_architecture():
    """Assert hexastack_graphql strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_graphql")
