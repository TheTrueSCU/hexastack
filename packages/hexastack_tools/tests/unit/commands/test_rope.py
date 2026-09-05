"""Unit tests for rope commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_tools.commands.rope import (
    alphabetize_main,
    get_line_offsets,
    get_offset,
    handle_change_signature,
    handle_extract_method,
    handle_extract_var,
    handle_find_occurrences,
    handle_inline,
    handle_move_module,
    handle_move_symbol,
    handle_rename,
    handle_use_function,
    run_main,
    sort_python_file,
)


def test_rope_callables() -> None:
    """Verify rope callables."""
    assert callable(alphabetize_main)
    assert callable(run_main)
    assert callable(sort_python_file)
    assert callable(get_line_offsets)
    assert callable(get_offset)
    assert callable(handle_rename)
    assert callable(handle_change_signature)
    assert callable(handle_extract_method)
    assert callable(handle_extract_var)
    assert callable(handle_find_occurrences)
    assert callable(handle_inline)
    assert callable(handle_move_module)
    assert callable(handle_move_symbol)
    assert callable(handle_use_function)


def test_cst_alphabetizer(tmp_path: Path) -> None:
    """Verify LibCST transformer alphabetizes functions and methods properly."""
    py_file = tmp_path / "sample.py"
    code = """
def zebra():
    pass

def alpha():
    pass

class MyClass:
    def __init__(self):
        pass

    def zoo(self):
        pass

    def bar(self):
        pass
"""
    py_file.write_text(code, encoding="utf-8")
    modified = sort_python_file(py_file)
    assert modified is True

    new_code = py_file.read_text(encoding="utf-8")
    assert new_code.find("def alpha") < new_code.find("def zebra")
    assert new_code.find("def bar") < new_code.find("def zoo")


def test_get_line_offsets(tmp_path: Path) -> None:
    """Verify character offset calculation."""
    f = tmp_path / "test.py"
    f.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")
    start, end = get_line_offsets(f, 1, 2)
    assert start == 0
    assert end == len("line 1\nline 2\n")


def test_get_offset(tmp_path: Path) -> None:
    """Verify column/line offset calculation."""
    f = tmp_path / "test.py"
    f.write_text("abc\ndef\n", encoding="utf-8")
    offset = get_offset(f, 2, 2)
    assert offset == len("abc\n") + 1


@patch(
    "sys.argv",
    [
        "rope-run",
        "rename",
        "--file",
        "foo.py",
        "--line",
        "1",
        "--col",
        "1",
        "--new-name",
        "bar",
    ],
)
@patch("hexastack_tools.commands.rope.handle_rename")
def test_rope_run_dispatch(mock_rename: MagicMock) -> None:
    """Verify rope run_main dispatches rename subcommand."""
    code = run_main()
    assert code == 0
    mock_rename.assert_called_once()
