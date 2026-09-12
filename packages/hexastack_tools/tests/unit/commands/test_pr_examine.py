"""Unit tests for pr_examine command."""

from unittest.mock import MagicMock, patch

from hexastack_tools.commands.pr_examine import examine_pr, main
from hexastack_tools.domain.github import ExaminePrReport, OutputFormat, PrSummary


def test_pr_examine_main_callable() -> None:
    """Verify pr examine main callable."""
    assert callable(main)


def test_examine_pr_dispatches_and_presents() -> None:
    """Verify examine_pr dispatches ExaminePrCommand and invokes presenter."""
    mock_bus = MagicMock()
    mock_summary = PrSummary(
        number=10,
        title="Test PR",
        author="alice",
        state="open",
        mergeable="mergeable",
        is_draft=False,
        head_ref="feature",
        base_ref="main",
        html_url="https://github.com/test/10",
    )
    mock_report = ExaminePrReport(summary=mock_summary)
    mock_bus.dispatch.return_value = mock_report

    mock_presenter = MagicMock()
    mock_presenter.present_pr_summary.return_value = 0

    with (
        patch(
            "hexastack_tools.commands.pr_examine.create_governance_bus",
            return_value=mock_bus,
        ),
        patch(
            "hexastack_tools.commands.pr_examine.create_github_presenter",
            return_value=mock_presenter,
        ),
    ):
        code = examine_pr(pr_number=10, output_format=OutputFormat.JSON, watch=False)

    assert code == 0
    mock_bus.dispatch.assert_called_once()
    mock_presenter.present_pr_summary.assert_called_once_with(mock_report)
