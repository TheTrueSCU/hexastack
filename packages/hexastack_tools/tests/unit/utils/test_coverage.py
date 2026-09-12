"""Unit tests for coverage diff hunk parsing utilities.

Notes/Architectural Intent:
    Verifies that parse_git_diff_hunks correctly extracts modified line numbers
    from unified diff format without requiring git repository state.
"""

from __future__ import annotations

from pathlib import Path

from hexastack_tools.utils.coverage import parse_git_diff_hunks


def test_parse_git_diff_hunks_empty(tmp_path: Path) -> None:
    """Verify empty diff produces empty mapping."""
    res = parse_git_diff_hunks("", tmp_path)
    assert res == {}


def test_parse_git_diff_hunks_single_file(tmp_path: Path) -> None:
    """Verify single-file diff with multiple hunks."""
    diff_text = """diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -10 +10,3 @@
+line10
+line11
+line12
@@ -25 +27 @@
+line27
"""
    res = parse_git_diff_hunks(diff_text, tmp_path)
    target_file = (tmp_path / "src/app.py").resolve()
    assert target_file in res
    assert res[target_file] == {10, 11, 12, 27}
