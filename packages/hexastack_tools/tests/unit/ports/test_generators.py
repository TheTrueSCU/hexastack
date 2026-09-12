"""Unit tests for generator port interfaces."""

from __future__ import annotations

import pytest

from hexastack_tools.domain.generators import (
    ArchonReport,
    PydepsReport,
    UsageDocsReport,
)
from hexastack_tools.ports.generators import GeneratorPresenterPort


class DummyGeneratorPresenter(GeneratorPresenterPort):
    """Concrete dummy presenter for testing abstract interface conformance."""

    def present_pydeps(self, report: PydepsReport) -> int:
        return 0 if report.is_successful else 1

    def present_usage_docs(self, report: UsageDocsReport) -> int:
        return 0 if report.is_valid else 1

    def present_archon(self, report: ArchonReport) -> int:
        return 0 if report.is_successful else 1


def test_generator_presenter_port_instantiation() -> None:
    """Verify GeneratorPresenterPort cannot be instantiated directly without implementations."""
    with pytest.raises(TypeError):
        GeneratorPresenterPort()  # type: ignore[abstract]


def test_concrete_generator_presenter() -> None:
    """Verify concrete subclass implements all abstract methods."""
    presenter = DummyGeneratorPresenter()
    assert presenter.present_pydeps(PydepsReport()) == 0
    assert presenter.present_usage_docs(UsageDocsReport()) == 0
    assert presenter.present_archon(ArchonReport()) == 0
