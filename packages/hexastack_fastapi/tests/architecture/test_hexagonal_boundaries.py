"""Hexagonal architecture boundary tests for hexastack_fastapi."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_fastapi_clean_architecture():
    """Assert hexastack_fastapi strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_fastapi")
