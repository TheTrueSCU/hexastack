"""Unit tests for codeql_scan command."""

from hexastack_tools.commands.codeql_scan import main


def test_codeql_scan_main_callable() -> None:
    """Verify codeql scanner main callable."""
    assert callable(main)


def test_codeql_scan_main_dispatches_bus() -> None:
    """Verify codeql scan main dispatches ScanCodeQlCommand and formats."""
    from unittest.mock import MagicMock, patch

    from hexastack_tools.domain.analysis import CodeQlScanReport

    mock_bus = MagicMock()
    mock_report = CodeQlScanReport(
        is_successful=True,
        findings_count=0,
        critical_count=0,
    )
    mock_bus.dispatch.return_value = mock_report

    with patch(
        "hexastack_tools.infra.bootstrap.create_governance_bus", return_value=mock_bus
    ):
        code = main(["--suite", "codeql/python-queries", "--format", "json"])
        assert code == 0
        assert mock_bus.dispatch.called
