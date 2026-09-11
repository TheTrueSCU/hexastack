"""Unit tests for all_statements utility functions.

Notes/Architectural Intent:
    Verifies that AST checks identify duplicate and out-of-order __all__ symbols,
    and that fix_file_all properly formats and alphabetizes declarations.
"""

from pathlib import Path

from hexastack_tools.utils.all_statements import check_file_all, fix_file_all


def test_check_file_all_clean(tmp_path: Path) -> None:
    """Verify clean sorted __all__ produces no errors."""
    f = tmp_path / "clean.py"
    f.write_text('__all__ = ["Alpha", "Beta"]\n', encoding="utf-8")
    assert check_file_all(f) == []


def test_check_file_all_out_of_order_and_duplicate(tmp_path: Path) -> None:
    """Verify out-of-order and duplicate symbols are caught."""
    f = tmp_path / "bad.py"
    f.write_text('__all__ = ["Beta", "Alpha", "Beta"]\n', encoding="utf-8")
    errors = check_file_all(f)
    assert len(errors) == 2


def test_fix_file_all_reformats(tmp_path: Path) -> None:
    """Verify fix_file_all sorts and deduplicates in-place."""
    f = tmp_path / "fixme.py"
    f.write_text('__all__ = ["Beta", "Alpha"]\n', encoding="utf-8")
    modified = fix_file_all(f)
    assert modified is True
    assert check_file_all(f) == []
