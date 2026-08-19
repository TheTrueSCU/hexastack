"""Hexagonal architecture boundary tests for hexastack_otel."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_otel_clean_architecture():
    """Assert hexastack_otel strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_otel")
