"""Unit tests for MutationInspectorPort interface.

Notes/Architectural Intent:
    Ensures MutationInspectorPort cannot be instantiated directly and that
    concrete subclasses fulfill abstract requirements.
"""

from __future__ import annotations

import pytest
from hexastack_qual.domain.models import MutantReport
from hexastack_qual.ports.mutator import MutationInspectorPort


class DummyMutator(MutationInspectorPort):
    """Concrete dummy implementation for interface testing."""

    def inspect_surviving_mutants(
        self,
        package: str | None = None,
        actionable_only: bool = True,
    ) -> MutantReport:
        return MutantReport(package_name="test", mutation_score=100.0)

    def run_mutation_testing(
        self,
        package: str | None = None,
        reset: bool = False,
    ) -> MutantReport:
        return MutantReport(package_name="test", mutation_score=100.0)


def test_mutation_inspector_port_cannot_instantiate_abstract() -> None:
    """Ensure abstract port cannot be instantiated directly."""
    with pytest.raises(TypeError):
        MutationInspectorPort()  # type: ignore[abstract]


def test_concrete_mutator_satisfies_contract() -> None:
    """Ensure concrete mutator satisfies port interface."""
    mutator = DummyMutator()
    inspect_res = mutator.inspect_surviving_mutants("core")
    run_res = mutator.run_mutation_testing("core")

    assert inspect_res.mutation_score == 100.0
    assert run_res.mutation_score == 100.0
