"""Unit tests for code_scanning command."""

from hexastack_tools.commands.code_scanning import (
    _build_alert_locations_table,
    _build_rule_summary_table,
    _filter_alerts,
    main,
)
from hexastack_tools.domain.github import SecurityAlert


def test_code_scanning_filtering() -> None:
    """Verify alert filtering by rule, package, and severity."""
    alert1 = SecurityAlert(
        number=1,
        rule_id="py/unused-import",
        rule_description="Unused import",
        severity="warning",
        security_severity_level=None,
        state="open",
        path="packages/hexastack_core/src/main.py",
        start_line=1,
        end_line=1,
        message="Import not used",
    )
    alert2 = SecurityAlert(
        number=2,
        rule_id="py/sql-injection",
        rule_description="SQL injection",
        severity="critical",
        security_severity_level="high",
        state="open",
        path="packages/hexastack_db/src/repo.py",
        start_line=10,
        end_line=12,
        message="Unescaped query",
    )
    alerts = [alert1, alert2]

    assert len(_filter_alerts(alerts, "unused", None, None)) == 1
    assert len(_filter_alerts(alerts, None, "hexastack_db", None)) == 1
    assert len(_filter_alerts(alerts, None, None, "critical")) == 1


def test_code_scanning_tables() -> None:
    """Verify summary and location table builders."""
    alert = SecurityAlert(
        number=10,
        rule_id="py/test-rule",
        rule_description="Test rule description",
        severity="warning",
        security_severity_level=None,
        state="open",
        path="packages/hexastack_core/src/test.py",
        start_line=5,
        end_line=5,
        message="Warning message",
    )
    by_rule = {"py/test-rule": [alert]}
    rule_table = _build_rule_summary_table(by_rule, "open", 1)
    assert rule_table.title is not None
    assert "Total: 1" in str(rule_table.title)

    loc_table = _build_alert_locations_table([alert])
    assert loc_table.title is not None


def test_code_scanning_main_callable() -> None:
    """Verify code scanning command entrypoint."""
    assert callable(main)
