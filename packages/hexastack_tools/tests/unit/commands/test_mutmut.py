from unittest.mock import MagicMock, patch

from hexastack_tools.commands.mutmut import (
    MutantCategory,
    classify_mutant_line,
    clear_package_cache,
    inspect_main,
    run_main,
    run_mutmut_on_package,
    show_file_mutants,
    show_summary,
)


def test_mutmut_callables() -> None:
    """Verify mutmut callables."""
    assert callable(inspect_main)
    assert callable(run_main)
    assert callable(clear_package_cache)
    assert callable(run_mutmut_on_package)
    assert callable(classify_mutant_line)
    assert callable(show_summary)
    assert callable(show_file_mutants)


def test_classify_mutant_line() -> None:
    """Verify classification heuristics for Ignorable, Equivalent, and Critical lines."""
    # Ignorable
    cat, _ = classify_mutant_line("logger.info('event received')", "src/foo.py")
    assert cat == MutantCategory.IGNORABLE

    cat, _ = classify_mutant_line("console.print('hello')", "src/foo.py")
    assert cat == MutantCategory.IGNORABLE

    cat, _ = classify_mutant_line("x = 1", "src/testing/harness.py")
    assert cat == MutantCategory.IGNORABLE

    # Equivalent
    cat, _ = classify_mutant_line("user = cast(User, raw_user)", "src/foo.py")
    assert cat == MutantCategory.EQUIVALENT

    cat, _ = classify_mutant_line(
        "def fn(val: str | None = None) -> None:", "src/foo.py"
    )
    assert cat == MutantCategory.EQUIVALENT

    cat, _ = classify_mutant_line("val = d.get('key', None)", "src/foo.py")
    assert cat == MutantCategory.EQUIVALENT

    # Critical
    cat, _ = classify_mutant_line("if user.is_authenticated:", "src/foo.py")
    assert cat == MutantCategory.CRITICAL

    cat, _ = classify_mutant_line("raise ValueError('Invalid token')", "src/foo.py")
    assert cat == MutantCategory.CRITICAL

    cat, _ = classify_mutant_line("count = total + 1", "src/foo.py")
    assert cat == MutantCategory.CRITICAL


@patch("subprocess.run")
@patch("sys.exit")
@patch("sys.argv", ["mutmut-run", "-p", "core"])
def test_mutmut_run_with_package(mock_exit: MagicMock, mock_run: MagicMock) -> None:
    """Verify mutmut run_main invokes mutmut run with targeted package path and runner."""
    mock_run.return_value.returncode = 0
    run_main()
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert call_args[0] == "mutmut"
    assert call_args[1] == "run"
    assert "--paths-to-mutate" in call_args
    idx = call_args.index("--paths-to-mutate")
    assert "hexastack_core/src" in call_args[idx + 1]
    assert "--runner" in call_args
    runner_idx = call_args.index("--runner")
    assert "hexastack_core/tests" in call_args[runner_idx + 1]
    mock_exit.assert_called_once_with(0)


@patch("subprocess.run")
@patch("sys.exit")
@patch("sys.argv", ["mutmut-run", "-a"])
def test_mutmut_run_all_packages(mock_exit: MagicMock, mock_run: MagicMock) -> None:
    """Verify mutmut run_main with -a executes sequentially per package."""
    mock_run.return_value.returncode = 0
    run_main()
    assert mock_run.call_count >= 1
    # Check that individual calls isolate paths-to-mutate to a single package
    for call in mock_run.call_args_list:
        args = call[0][0]
        assert args[0] == "mutmut"
        assert args[1] == "run"
        assert "--paths-to-mutate" in args
        idx = args.index("--paths-to-mutate")
        assert ":" not in args[idx + 1]
    mock_exit.assert_called_once_with(0)


@patch("hexastack_tools.commands.mutmut.get_db_connection")
@patch("hexastack_tools.commands.mutmut.show_summary")
@patch("sys.argv", ["mutmut-inspect", "--summary"])
def test_mutmut_inspect_summary(
    mock_summary: MagicMock, mock_get_conn: MagicMock
) -> None:
    """Verify mutmut inspect_main invokes show_summary when --summary is passed."""
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    inspect_main()
    mock_summary.assert_called_once_with(mock_conn)
    mock_conn.close.assert_called_once()


@patch("hexastack_tools.commands.mutmut.get_db_connection")
@patch("hexastack_tools.commands.mutmut.show_file_mutants")
@patch("sys.argv", ["mutmut-inspect", "-p", "core", "-a"])
def test_mutmut_inspect_package_actionable(
    mock_show_file: MagicMock, mock_get_conn: MagicMock
) -> None:
    """Verify mutmut inspect_main invokes show_file_mutants with package and actionable flag."""
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    inspect_main()
    mock_show_file.assert_called_once_with(
        mock_conn, "hexastack_core", limit=25, actionable_only=True
    )
    mock_conn.close.assert_called_once()


@patch("hexastack_tools.commands.mutmut._revert_bak_and_disk_mutations")
@patch("subprocess.run", side_effect=KeyboardInterrupt)
@patch("sys.exit")
@patch("sys.argv", ["mutmut-run", "-p", "core"])
def test_mutmut_keyboard_interrupt(
    mock_exit: MagicMock,
    mock_run: MagicMock,
    mock_revert: MagicMock,
) -> None:
    """Verify mutmut run_main handles KeyboardInterrupt cleanly by reverting disk mutations."""
    run_main()
    assert mock_revert.called
    mock_exit.assert_called_once_with(130)
