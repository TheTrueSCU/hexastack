"""Unit tests for domain refactoring models and CQRS commands."""

from __future__ import annotations

from pathlib import Path

from hexastack_tools.domain.refactoring import (
    AlphabetizeCodeCommand,
    AlphabetizeCodeReport,
    MediumPublishReport,
    PublishMediumArticlesCommand,
)


def test_alphabetize_domain_models() -> None:
    """Verify AlphabetizeCodeReport and AlphabetizeCodeCommand."""
    rep = AlphabetizeCodeReport(
        reordered_files=("src/foo.py",),
        unchanged_files=("src/bar.py",),
        is_successful=True,
    )
    assert len(rep.reordered_files) == 1
    assert len(rep.unchanged_files) == 1
    assert rep.is_successful is True

    cmd = AlphabetizeCodeCommand(targets=(Path("src/foo.py"),), dry_run=True)
    assert len(cmd.targets) == 1
    assert cmd.dry_run is True


def test_medium_publish_domain_models() -> None:
    """Verify MediumPublishReport and PublishMediumArticlesCommand."""
    rep = MediumPublishReport(
        published_count=3,
        total_count=3,
        is_successful=True,
        details=(("article-1", "https://dev.to/1"),),
    )
    assert rep.published_count == 3
    assert rep.is_successful is True

    cmd = PublishMediumArticlesCommand(dry_run=False, publish=True)
    assert cmd.dry_run is False
    assert cmd.publish is True
