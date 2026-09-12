"""Unit tests for analysis port interfaces."""

from __future__ import annotations

import pytest

from hexastack_tools.domain.analysis import (
    CodeQlScanReport,
    FuzzRunReport,
    InlineSnapshotsReport,
)
from hexastack_tools.ports.analysis import AnalysisPresenterPort


class DummyAnalysisPresenter(AnalysisPresenterPort):
    """Concrete dummy presenter for testing abstract interface conformance."""

    def present_codeql(self, report: CodeQlScanReport) -> int:
        return 0 if report.is_successful else 1

    def present_fuzz(self, report: FuzzRunReport) -> int:
        return 0 if report.all_passed else 1

    def present_inline_snapshots(self, report: InlineSnapshotsReport) -> int:
        return report.exit_code


def test_analysis_presenter_port_instantiation() -> None:
    """Verify AnalysisPresenterPort cannot be instantiated directly without implementations."""
    with pytest.raises(TypeError):
        AnalysisPresenterPort()  # type: ignore[abstract]


def test_concrete_analysis_presenter() -> None:
    """Verify concrete subclass implements all abstract methods."""
    presenter = DummyAnalysisPresenter()
    assert presenter.present_codeql(CodeQlScanReport()) == 0
    assert presenter.present_fuzz(FuzzRunReport()) == 0
    assert presenter.present_inline_snapshots(InlineSnapshotsReport()) == 0
