"""Unit tests for architectural testing utilities."""

from hexastack_core.testing.architecture import (
    assert_clean_architecture,
    get_layer_restrictions,
)


def test_architecture_testing_utilities() -> None:
    assert callable(assert_clean_architecture)
    restrictions = get_layer_restrictions()
    assert "domain" in restrictions
    assert "ports" in restrictions
