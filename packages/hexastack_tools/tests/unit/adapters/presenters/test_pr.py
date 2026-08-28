"""Unit tests for hexastack_tools PR presenter."""

from hexastack_tools.adapters.presenters.pr import (
    _build_checks_table,
    _build_threads_table,
    _render_check_conclusion,
    present_pr_summary,
    render_pr_summary_json,
    render_pr_summary_plain,
    render_pr_summary_rich,
)
from hexastack_tools.domain.github import (
    CheckRunFinding,
    OutputFormat,
    PRSummary,
    ReviewComment,
    ReviewThread,
)


def test_render_check_conclusions() -> None:
    """Verify conclusion string badge styling."""
    assert "SUCCESS" in _render_check_conclusion("success")
    assert "FAILURE" in _render_check_conclusion("failure")
    assert "SKIPPED" in _render_check_conclusion("skipped")
    assert "NEUTRAL" in _render_check_conclusion("neutral")
    assert "PENDING" in _render_check_conclusion("pending")


def test_build_checks_table() -> None:
    """Verify checks table construction."""
    check = CheckRunFinding(
        name="Unit Tests",
        status="completed",
        conclusion="success",
        details_url="https://ci.example.com",
    )
    table = _build_checks_table((check,))
    assert table.title is not None
    assert "1 checks" in str(table.title)


def test_build_threads_table() -> None:
    """Verify threads table construction."""
    comment = ReviewComment(
        id=1,
        author="alice",
        body="LGTM",
        created_at="2026-08-28T00:00:00Z",
        path="src/main.py",
        line=10,
    )
    thread = ReviewThread(
        id="T1",
        is_resolved=True,
        resolved_by="alice",
        comments=(comment,),
    )
    table = _build_threads_table((thread,))
    assert table.title is not None
    assert "1 threads" in str(table.title)


def test_render_pr_summary_rich() -> None:
    """Verify Rich rendering execution."""
    comment = ReviewComment(
        id=2,
        author="bot",
        body="Fix this issue",
        created_at="2026-08-28T00:00:00Z",
        path="src/main.py",
        line=20,
    )
    thread = ReviewThread(
        id="T2",
        is_resolved=False,
        resolved_by=None,
        comments=(comment,),
    )
    check = CheckRunFinding(
        name="Linter",
        status="completed",
        conclusion="failure",
        details_url="https://ci.example.com",
    )
    summary = PRSummary(
        number=41,
        title="fix(security): test",
        author="alice",
        state="open",
        mergeable="clean",
        is_draft=False,
        head_ref="fix/test",
        base_ref="main",
        html_url="https://github.com/pr/41",
        check_runs=(check,),
        review_threads=(thread,),
    )
    render_pr_summary_rich(summary, show_details=True)


def test_render_pr_summary_json_and_plain() -> None:
    """Verify PRSummary JSON and plain serialization format."""
    comment = ReviewComment(
        id=3,
        author="alice",
        body="LGTM",
        created_at="2026-08-28T00:00:00Z",
        path="src/main.py",
        line=10,
    )
    thread = ReviewThread(
        id="T3",
        is_resolved=True,
        resolved_by="alice",
        comments=(comment,),
    )
    check = CheckRunFinding(
        name="Linter",
        status="completed",
        conclusion="success",
        details_url="https://ci.example.com",
    )
    summary = PRSummary(
        number=41,
        title="fix(security): test",
        author="alice",
        state="open",
        mergeable="clean",
        is_draft=False,
        head_ref="fix/test",
        base_ref="main",
        html_url="https://github.com/pr/41",
        check_runs=(check,),
        review_threads=(thread,),
    )
    json_str = render_pr_summary_json(summary)
    assert '"number": 41' in json_str
    assert '"is_clean": true' in json_str

    plain_str = render_pr_summary_plain(summary)
    assert "PR\t41\topen" in plain_str
    assert "CHECK\tCI\tLinter" in plain_str
    assert "THREAD\tT3\tRESOLVED" in plain_str

    present_pr_summary(summary, OutputFormat.RICH)
    present_pr_summary(summary, OutputFormat.JSON)
    present_pr_summary(summary, OutputFormat.PLAIN)
