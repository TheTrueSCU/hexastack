"""Hexagonal architecture boundary tests for hexastack_logging."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_logging_clean_architecture():
    """Assert hexastack_logging strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_logging")
