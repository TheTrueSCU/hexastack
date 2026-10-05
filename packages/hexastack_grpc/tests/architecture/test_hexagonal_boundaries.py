"""Hexagonal architecture boundary tests for hexastack_grpc."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_grpc_clean_architecture():
    """Assert hexastack_grpc strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_grpc")
