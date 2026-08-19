"""Hexagonal architecture boundary tests for hexastack_flags."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_flags_clean_architecture():
    """Assert hexastack_flags strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_flags")
