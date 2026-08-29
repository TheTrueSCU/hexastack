"""Unit tests for hexastack_tools domain models."""

from hexastack_tools.domain.github import (
    CheckRunFinding,
    PrSummary,
    ReviewThread,
)


def test_pr_summary_is_clean() -> None:
    """Verify PrSummary cleanliness calculation with checks and review threads."""
    check = CheckRunFinding(
        name="build",
        status="completed",
        conclusion="success",
        details_url="https://ci.example.com",
    )
    resolved_thread = ReviewThread(
        id="T1",
        is_resolved=True,
        resolved_by="reviewer",
    )
    summary = PrSummary(
        number=1,
        title="Test PR",
        author="alice",
        state="open",
        mergeable="clean",
        is_draft=False,
        head_ref="feat/test",
        base_ref="main",
        html_url="https://github.com/org/repo/pull/1",
        check_runs=(check,),
        review_threads=(resolved_thread,),
    )
    assert summary.is_clean is True


def test_pr_summary_unresolved_thread_is_not_clean() -> None:
    """Verify PrSummary with unresolved thread is marked unclean."""
    unresolved_thread = ReviewThread(
        id="T2",
        is_resolved=False,
        resolved_by=None,
    )
    summary = PrSummary(
        number=2,
        title="Test PR Unclean",
        author="bob",
        state="open",
        mergeable="clean",
        is_draft=False,
        head_ref="feat/test2",
        base_ref="main",
        html_url="https://github.com/org/repo/pull/2",
        review_threads=(unresolved_thread,),
    )
    assert summary.is_clean is False
