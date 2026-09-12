"""Unit tests for testing presenters across Rich, JSON, and Markdown formats.

Notes/Architectural Intent:
    Verifies that all presenter adapters correctly format mutation summaries,
    boundary leaks, redundancy audits, and test impact reports.
"""

from __future__ import annotations

import io

from rich.console import Console

from hexastack_tools.adapters.presenters.testing import (
    JsonTestingPresenterAdapter,
    MarkdownTestingPresenterAdapter,
    RichTestingPresenterAdapter,
    create_testing_presenter,
)
from hexastack_tools.domain.testing import (
    BoundaryAuditItem,
    BoundaryAuditReport,
    ImpactedTestsReport,
    MutantCategory,
    MutantRecord,
    MutationAuditReport,
    MutationPackageSummary,
    RedundancyAuditReport,
)


def _sample_report() -> MutationAuditReport:
    summary = MutationPackageSummary("hexastack_core", 5, 1, 2, 2)
    mutant = MutantRecord(
        id="42",
        filename="packages/core/src/service.py",
        line_number=10,
        line_content="if token is None:",
        category=MutantCategory.CRITICAL,
        rationale="Control flow",
        covering_tests=("test_foo",),
    )
    return MutationAuditReport((summary,), (mutant,))


def test_create_testing_presenter():
    """Verify presenter factory returns correct adapter instance."""
    assert isinstance(create_testing_presenter("table"), RichTestingPresenterAdapter)
    assert isinstance(create_testing_presenter("json"), JsonTestingPresenterAdapter)
    assert isinstance(
        create_testing_presenter("markdown"), MarkdownTestingPresenterAdapter
    )


def test_rich_mutation_presenter():
    """Verify RichTestingPresenterAdapter outputs tables and exits appropriately."""
    buf = io.StringIO()
    console = Console(file=buf, color_system=None)
    presenter = RichTestingPresenterAdapter(console)

    report = _sample_report()
    code1 = presenter.present_mutation_summary(report)
    assert code1 == 1
    assert "hexastack_core" in buf.getvalue()

    code2 = presenter.present_actionable_mutants(report)
    assert code2 == 1
    assert "Actionable Surviving Mutants" in buf.getvalue()


def test_json_mutation_presenter():
    """Verify JsonTestingPresenterAdapter serializes valid JSON."""
    buf = io.StringIO()
    console = Console(file=buf, color_system=None)
    presenter = JsonTestingPresenterAdapter(console)

    report = _sample_report()
    presenter.present_mutation_summary(report)
    assert '"total_critical": 1' in buf.getvalue()


def test_markdown_mutation_presenter():
    """Verify MarkdownTestingPresenterAdapter generates Markdown tables."""
    buf = io.StringIO()
    console = Console(file=buf, color_system=None)
    presenter = MarkdownTestingPresenterAdapter(console)

    report = _sample_report()
    presenter.present_mutation_summary(report)
    assert "| `hexastack_core` | 5 | 1 | 2 | 2 |" in buf.getvalue()


def test_boundary_audit_presenters():
    """Verify boundary audit presentations."""
    buf = io.StringIO()
    console = Console(file=buf, color_system=None)
    rich_p = RichTestingPresenterAdapter(console)
    json_p = JsonTestingPresenterAdapter(console)

    clean = BoundaryAuditReport(leaks=())
    assert rich_p.present_boundary_audit(clean) == 0

    leaky = BoundaryAuditReport(leaks=(BoundaryAuditItem("test_1", "leak.py"),))
    assert rich_p.present_boundary_audit(leaky) == 1
    assert json_p.present_boundary_audit(leaky) == 1


def test_redundancy_and_impact_presenters():
    """Verify redundancy and impact analysis presentations."""
    buf = io.StringIO()
    console = Console(file=buf, color_system=None)
    rich_p = RichTestingPresenterAdapter(console)

    red = RedundancyAuditReport(redundant_tests=("test_foo",))
    assert rich_p.present_redundancy_audit(red) == 0

    impact = ImpactedTestsReport(
        changed_files=("mod.py",),
        impacted_tests=("test_foo",),
        dry_run=True,
    )
    assert rich_p.present_impact_analysis(impact) == 0
