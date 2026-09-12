"""Unit tests for multi-format refactoring presenters."""

from __future__ import annotations

from unittest.mock import MagicMock

from rich.console import Console

from hexastack_tools.adapters.presenters.refactoring import (
    JsonRefactoringPresenterAdapter,
    MarkdownRefactoringPresenterAdapter,
    RichRefactoringPresenterAdapter,
    create_refactoring_presenter,
)
from hexastack_tools.domain.refactoring import (
    AlphabetizeCodeReport,
    MediumPublishReport,
)


def test_create_refactoring_presenter_factory() -> None:
    """Verify create_refactoring_presenter instantiates correct adapter."""
    assert isinstance(
        create_refactoring_presenter("rich"), RichRefactoringPresenterAdapter
    )
    assert isinstance(
        create_refactoring_presenter("table"), RichRefactoringPresenterAdapter
    )
    assert isinstance(
        create_refactoring_presenter("json"), JsonRefactoringPresenterAdapter
    )
    assert isinstance(
        create_refactoring_presenter("markdown"), MarkdownRefactoringPresenterAdapter
    )
    assert isinstance(
        create_refactoring_presenter("md"), MarkdownRefactoringPresenterAdapter
    )


def test_rich_refactoring_presenter() -> None:
    """Verify RichRefactoringPresenterAdapter renders reports."""
    mock_console = MagicMock(spec=Console)
    presenter = RichRefactoringPresenterAdapter(console=mock_console)

    alpha_ok = AlphabetizeCodeReport(
        reordered_files=("src/foo.py",),
        unchanged_files=("src/bar.py",),
        is_successful=True,
    )
    assert presenter.present_alphabetize(alpha_ok) == 0

    alpha_err = AlphabetizeCodeReport(is_successful=False)
    assert presenter.present_alphabetize(alpha_err) == 1

    pub_ok = MediumPublishReport(
        published_count=1,
        total_count=1,
        is_successful=True,
        details=(("art", "url"),),
    )
    assert presenter.present_medium_publish(pub_ok) == 0

    pub_err = MediumPublishReport(is_successful=False)
    assert presenter.present_medium_publish(pub_err) == 1


def test_json_refactoring_presenter() -> None:
    """Verify JsonRefactoringPresenterAdapter formats output as JSON."""
    mock_console = MagicMock(spec=Console)
    presenter = JsonRefactoringPresenterAdapter(console=mock_console)

    alpha_ok = AlphabetizeCodeReport(is_successful=True)
    assert presenter.present_alphabetize(alpha_ok) == 0
    mock_console.print_json.assert_called()

    pub_ok = MediumPublishReport(is_successful=True)
    assert presenter.present_medium_publish(pub_ok) == 0


def test_markdown_refactoring_presenter() -> None:
    """Verify MarkdownRefactoringPresenterAdapter formats output as Markdown."""
    mock_console = MagicMock(spec=Console)
    presenter = MarkdownRefactoringPresenterAdapter(console=mock_console)

    alpha_ok = AlphabetizeCodeReport(
        reordered_files=("src/foo.py",),
        is_successful=True,
    )
    assert presenter.present_alphabetize(alpha_ok) == 0
    mock_console.print.assert_called()

    pub_ok = MediumPublishReport(
        details=(("art", "url"),),
        is_successful=True,
    )
    assert presenter.present_medium_publish(pub_ok) == 0
