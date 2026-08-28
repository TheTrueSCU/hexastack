"""Unit tests for hexastack_tools domain models."""

from hexastack_tools.domain.github import (
    CheckRunFinding,
    PRSummary,
    ReviewThread,
)


def test_pr_summary_is_clean() -> None:
    """Verify PRSummary cleanliness calculation with checks and review threads."""
    clean_check = CheckRunFinding(
        name="CI",
        status="completed",
        conclusion="success",
        details_url="https://github.com",
    )
    resolved_thread = ReviewThread(
        id="T1",
        is_resolved=True,
        resolved_by="reviewer",
    )
    summary = PRSummary(
        number=1,
        title="feat: test",
        author="alice",
        state="open",
        mergeable="clean",
        is_draft=False,
        head_ref="feat/test",
        base_ref="main",
        html_url="https://github.com/pr/1",
        check_runs=(clean_check,),
        review_threads=(resolved_thread,),
    )
    assert summary.is_clean is True


def test_pr_summary_unresolved_thread_is_not_clean() -> None:
    """Verify PRSummary with unresolved thread is marked unclean."""
    unresolved_thread = ReviewThread(
        id="T2",
        is_resolved=False,
        resolved_by=None,
    )
    summary = PRSummary(
        number=2,
        title="feat: test",
        author="alice",
        state="open",
        mergeable="clean",
        is_draft=False,
        head_ref="feat/test",
        base_ref="main",
        html_url="https://github.com/pr/2",
        review_threads=(unresolved_thread,),
    )
    assert summary.is_clean is False
