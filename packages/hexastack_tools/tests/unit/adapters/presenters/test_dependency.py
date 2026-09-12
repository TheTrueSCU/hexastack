"""Unit tests for multi-format dependency presenters.

Notes/Architectural Intent:
    Verifies that Rich, JSON, and Markdown presenters format extras parity,
    deptry, import-linter, and unified dependency audits correctly.
"""

from __future__ import annotations

import json
from io import StringIO

import pytest
from rich.console import Console

from hexastack_tools.adapters.presenters.dependency import (
    JsonDependencyPresenterAdapter,
    MarkdownDependencyPresenterAdapter,
    RichDependencyPresenterAdapter,
    create_dependency_presenter,
)
from hexastack_tools.domain.dependencies import (
    DependencyAuditItem,
    DeptryAuditReport,
    DeptryPackageResult,
    ExtraParityViolation,
    ExtrasAuditResult,
    ImportLinterPackageResult,
    ImportLinterReport,
    UnifiedDependencyAuditReport,
)


def test_rich_dependency_presenter_all():
    """Verify Rich presenter outputs."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    presenter = RichDependencyPresenterAdapter(console=console)

    # 1. Extras parity clean & violation
    v = ExtraParityViolation("db", "sqlite", ("aiosqlite",), "Fix me")
    assert (
        presenter.present_extras_parity(
            ExtrasAuditResult(violations=(), total_packages_checked=5)
        )
        == 0
    )
    assert "properly forwarded" in buf.getvalue()

    buf.truncate(0)
    buf.seek(0)
    assert (
        presenter.present_extras_parity(
            ExtrasAuditResult(violations=(v,), total_packages_checked=5)
        )
        == 1
    )
    assert "Optional Extras Parity Violations" in buf.getvalue()

    # 2. Deptry
    d_ok = DeptryAuditReport(results=(DeptryPackageResult("core", True),), exit_code=0)
    assert presenter.present_deptry_audit(d_ok) == 0

    # 3. Import linter
    il = ImportLinterReport(
        results=(ImportLinterPackageResult("cqrs", True),), exit_code=0
    )
    assert presenter.present_import_linter(il) == 0

    # 4. Unified audit
    item = DependencyAuditItem("Tools", True)
    u_ok = UnifiedDependencyAuditReport(items=(item,), errors=(), is_healthy=True)
    assert presenter.present_unified_deps_audit(u_ok) == 0


def test_json_dependency_presenter_all():
    """Verify JSON presenter serializes valid JSON."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    presenter = JsonDependencyPresenterAdapter(console=console)

    v = ExtraParityViolation("db", "sqlite", ("aiosqlite",), "Fix me")
    res = ExtrasAuditResult(violations=(v,), total_packages_checked=5)
    assert presenter.present_extras_parity(res) == 1
    data = json.loads(buf.getvalue())
    assert data["status"] == "FAIL"
    assert data["violations"][0]["subpackage"] == "db"

    buf.truncate(0)
    buf.seek(0)
    d = DeptryAuditReport(results=(DeptryPackageResult("core", True),), exit_code=0)
    assert presenter.present_deptry_audit(d) == 0
    assert json.loads(buf.getvalue())["status"] == "PASS"


def test_markdown_dependency_presenter_all():
    """Verify Markdown presenter outputs formatted markdown."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    presenter = MarkdownDependencyPresenterAdapter(console=console)

    v = ExtraParityViolation("db", "sqlite", ("aiosqlite",), "Fix me")
    res = ExtrasAuditResult(violations=(v,), total_packages_checked=5)
    assert presenter.present_extras_parity(res) == 1
    assert "| Subpackage | Extra |" in buf.getvalue()

    buf.truncate(0)
    buf.seek(0)
    assert presenter.present_extras_parity(res, diagram="```mermaid\n```") == 0
    assert "mermaid" in buf.getvalue()


def test_create_dependency_presenter_factory():
    """Verify create_dependency_presenter factory."""
    assert isinstance(
        create_dependency_presenter("table"), RichDependencyPresenterAdapter
    )
    assert isinstance(
        create_dependency_presenter("json"), JsonDependencyPresenterAdapter
    )
    assert isinstance(
        create_dependency_presenter("markdown"), MarkdownDependencyPresenterAdapter
    )
    assert isinstance(
        create_dependency_presenter("md"), MarkdownDependencyPresenterAdapter
    )

    with pytest.raises(ValueError, match="Unsupported dependency presenter format"):
        create_dependency_presenter("invalid")
