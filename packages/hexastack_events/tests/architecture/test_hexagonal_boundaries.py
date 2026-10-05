"""Hexagonal architecture boundary tests for hexastack_events."""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_events_clean_architecture():
    """Assert hexastack_events strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_events")
