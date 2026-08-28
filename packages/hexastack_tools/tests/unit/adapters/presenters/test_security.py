"""Unit tests for security presenter."""

from hexastack_tools.adapters.presenters.security import (
    build_security_comments_table,
    present_security_comments,
    render_security_comments_json,
    render_security_comments_plain,
)
from hexastack_tools.domain.github import OutputFormat, ReviewComment, ReviewThread


def test_security_presenter_formats() -> None:
    """Verify rich, json, and plain presentation for security review comments."""
    comment = ReviewComment(
        id=101,
        author="security-bot",
        body="Potential SQL injection detected",
        created_at="2026-08-28T00:00:00Z",
        path="src/repo.py",
        line=42,
    )
    thread = ReviewThread(
        id="TH1",
        is_resolved=False,
        comments=(comment,),
        resolved_by=None,
    )
    threads = (thread,)

    table = build_security_comments_table(threads, 40)
    assert table.title is not None

    json_out = render_security_comments_json(threads, 40)
    assert '"pr_number": 40' in json_out
    assert '"security-bot"' in json_out

    plain_out = render_security_comments_plain(threads, 40)
    assert "PR\t40\t1" in plain_out
    assert "THREAD\tTH1\tUNRESOLVED\tsecurity-bot" in plain_out

    present_security_comments(threads, 40, OutputFormat.RICH)
    present_security_comments(threads, 40, OutputFormat.JSON)
    present_security_comments(threads, 40, OutputFormat.PLAIN)
    present_security_comments((), 40, OutputFormat.RICH)
