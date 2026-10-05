"""Unit tests for hypothesis testing utilities."""

from hexastack_core.testing.hypothesis import (
    cqrs_strategy,
    flag_scope,
    parametrize_flags,
)


def test_hypothesis_testing_helpers() -> None:
    assert callable(cqrs_strategy)
    assert callable(flag_scope)
    assert callable(parametrize_flags)
