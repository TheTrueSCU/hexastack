"""Unit tests for coverage, test impact, and boundary audit commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_tools.commands.coverage import (
    audit_layer_boundary_leaks,
    audit_redundant_tests,
    boundary_audit_main,
    find_impacted_tests,
    get_changed_lines,
    get_tests_covering_line,
    impact_main,
    redundancy_audit_main,
)


def test_coverage_callables() -> None:
    """Verify coverage command callables."""
    assert callable(audit_layer_boundary_leaks)
    assert callable(audit_redundant_tests)
    assert callable(boundary_audit_main)
    assert callable(find_impacted_tests)
    assert callable(get_changed_lines)
    assert callable(get_tests_covering_line)
    assert callable(impact_main)
    assert callable(redundancy_audit_main)


@patch("subprocess.run")
def test_get_changed_lines(mock_run: MagicMock, tmp_path: Path) -> None:
    """Verify changed lines parser from git diff output."""
    diff_output = """diff --git a/packages/hexastack_core/src/hexastack_core/domain/model.py b/packages/hexastack_core/src/hexastack_core/domain/model.py
--- a/packages/hexastack_core/src/hexastack_core/domain/model.py
+++ b/packages/hexastack_core/src/hexastack_core/domain/model.py
@@ -10,3 +10,4 @@
+class NewEntity:
+    pass
"""
    mock_run.return_value.stdout = diff_output
    changed = get_changed_lines(root_dir=tmp_path)
    assert len(changed) == 1
    target_file = (
        tmp_path / "packages/hexastack_core/src/hexastack_core/domain/model.py"
    ).resolve()
    assert target_file in changed
    assert set(range(10, 14)).issubset(changed[target_file])


def test_find_impacted_tests_nonexistent_cov(tmp_path: Path) -> None:
    """Verify empty test set returned when .coverage DB does not exist."""
    res = find_impacted_tests(
        {tmp_path / "foo.py": {1, 2}}, cov_path=tmp_path / ".coverage"
    )
    assert res == set()


def test_get_tests_covering_line_nonexistent_cov(tmp_path: Path) -> None:
    """Verify empty test list returned when .coverage DB does not exist."""
    res = get_tests_covering_line(
        tmp_path / "foo.py", 1, cov_path=tmp_path / ".coverage"
    )
    assert res == []


def test_audit_layer_boundary_leaks_nonexistent_cov(tmp_path: Path) -> None:
    """Verify empty list when .coverage DB is absent."""
    res = audit_layer_boundary_leaks(cov_path=tmp_path / ".coverage")
    assert res == []


def test_audit_redundant_tests_nonexistent_cov(tmp_path: Path) -> None:
    """Verify empty list when .coverage DB is absent."""
    res = audit_redundant_tests(cov_path=tmp_path / ".coverage")
    assert res == []
