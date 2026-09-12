"""Unit tests for SubprocessToolRunnerAdapter.

Notes/Architectural Intent:
    Verifies that SubprocessToolRunnerAdapter invokes tools, captures stdout/stderr,
    parses return codes and complexipy metrics, and constructs CheckResult objects.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_tools.adapters.runners.subprocess_runner import (
    SubprocessToolRunnerAdapter,
    _execute_subprocess,
    find_executable,
)
from hexastack_tools.domain.governance import CheckStatus, SanityTarget


def test_find_executable_fallback(monkeypatch):
    """Verify find_executable falls back to PATH or tool name when not in venv."""
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")
    res = find_executable("nonexistent_binary_xyz")
    assert res == "/usr/bin/nonexistent_binary_xyz"

    monkeypatch.setattr("shutil.which", lambda name: None)
    res_none = find_executable("nonexistent_binary_xyz")
    assert res_none == "nonexistent_binary_xyz"


def test_execute_subprocess_success_and_exception():
    """Verify _execute_subprocess handles normal runs and exceptions gracefully."""
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock(returncode=0, stdout="out", stderr="")
        mock_run.return_value = mock_proc
        code, out, err, dur = _execute_subprocess(["echo", "hello"])
        assert code == 0
        assert out == "out"
        assert dur >= 0.0

    with patch("subprocess.run", side_effect=OSError("Process failed")):
        code, out, err, dur = _execute_subprocess(["fail"])
        assert code == 1
        assert "Process failed" in err


def test_run_ruff_success_and_failures(tmp_path: Path):
    """Verify run_ruff handles success, lint failures, and formatting failures."""
    adapter = SubprocessToolRunnerAdapter()
    sample_file = tmp_path / "foo.py"
    sample_file.write_text("a = 1\n", encoding="utf-8")

    # 1. Skip when no paths
    skip_res = adapter.run_ruff((tmp_path / "missing.py",), "pkg")
    assert skip_res.status == CheckStatus.SKIP

    # 2. Success
    with patch(
        "hexastack_tools.adapters.runners.subprocess_runner._execute_subprocess"
    ) as mock_exec:
        mock_exec.return_value = (0, "", "", 0.05)
        res = adapter.run_ruff((sample_file,), "pkg", fix=True)
        assert res.status == CheckStatus.PASS

    # 3. Lint failure
    with patch(
        "hexastack_tools.adapters.runners.subprocess_runner._execute_subprocess"
    ) as mock_exec:
        mock_exec.return_value = (1, "E501 line too long", "", 0.05)
        res = adapter.run_ruff((sample_file,), "pkg")
        assert res.status == CheckStatus.FAIL
        assert "Lint errors detected" in res.details

    # 4. Format failure
    with patch(
        "hexastack_tools.adapters.runners.subprocess_runner._execute_subprocess"
    ) as mock_exec:
        mock_exec.side_effect = [(0, "", "", 0.05), (1, "would reformat", "", 0.05)]
        res = adapter.run_ruff((sample_file,), "pkg")
        assert res.status == CheckStatus.FAIL
        assert "Formatting required" in res.details


def test_run_ty_success_and_failure(tmp_path: Path):
    """Verify run_ty static typecheck parsing."""
    adapter = SubprocessToolRunnerAdapter()
    sample_file = tmp_path / "bar.py"
    sample_file.write_text("x: int = 1\n", encoding="utf-8")

    skip_res = adapter.run_ty((tmp_path / "nonexistent.py",), "pkg")
    assert skip_res.status == CheckStatus.SKIP

    with patch(
        "hexastack_tools.adapters.runners.subprocess_runner._execute_subprocess"
    ) as mock_exec:
        mock_exec.return_value = (0, "All checks passed", "", 0.1)
        res = adapter.run_ty((sample_file,), "pkg")
        assert res.status == CheckStatus.PASS

    with patch(
        "hexastack_tools.adapters.runners.subprocess_runner._execute_subprocess"
    ) as mock_exec:
        mock_exec.return_value = (1, "Type error on line 1", "", 0.1)
        res = adapter.run_ty((sample_file,), "pkg")
        assert res.status == CheckStatus.FAIL


def test_run_complexipy_violations(tmp_path: Path):
    """Verify run_complexipy threshold parsing."""
    adapter = SubprocessToolRunnerAdapter()
    sample_file = tmp_path / "mod.py"
    sample_file.write_text("def f(): pass\n", encoding="utf-8")

    skip_res = adapter.run_complexipy((tmp_path / "missing.py",), "pkg")
    assert skip_res.status == CheckStatus.SKIP

    cpx_output = "src/pkg/mod.py heavy_function 35\nsrc/pkg/mod.py simple_function 4\n"
    with patch(
        "hexastack_tools.adapters.runners.subprocess_runner._execute_subprocess"
    ) as mock_exec:
        mock_exec.return_value = (0, cpx_output, "", 0.15)
        res = adapter.run_complexipy((sample_file,), "pkg", max_complexity=25)
        assert res.status == CheckStatus.FAIL
        assert "1 function(s) exceed complexity 25" in res.details
        assert "heavy_function" in res.error_output


def test_run_all_statements_and_parity(tmp_path: Path):
    """Verify run_all_statements and run_test_parity adapter methods."""
    adapter = SubprocessToolRunnerAdapter()
    py_file = tmp_path / "lib.py"
    py_file.write_text("__all__ = ['b', 'a']\n", encoding="utf-8")

    with (
        patch(
            "hexastack_tools.adapters.runners.subprocess_runner.check_file_all",
            return_value=["__all__ out of order"],
        ),
        patch("hexastack_tools.adapters.runners.subprocess_runner.fix_file_all"),
    ):
        res = adapter.run_all_statements((py_file,), "lib", fix=True)
        assert res.status == CheckStatus.FAIL
        assert "1 __all__ violation(s)" in res.details

    target = SanityTarget("pkg", "package", tmp_path, (tmp_path,), ())
    with patch(
        "hexastack_tools.adapters.runners.subprocess_runner.check_package_parity",
        return_value=[],
    ):
        parity_res = adapter.run_test_parity(target, tmp_path)
        assert parity_res.status == CheckStatus.PASS

    file_target = SanityTarget("file.py", "file", py_file, (py_file,), ())
    skip_parity = adapter.run_test_parity(file_target, tmp_path)
    assert skip_parity.status == CheckStatus.SKIP


def test_run_pytest_variations(tmp_path: Path):
    """Verify run_pytest for package, example, file, and skipped executions."""
    adapter = SubprocessToolRunnerAdapter()
    pkg_target = SanityTarget("cqrs", "package", tmp_path, (tmp_path,), ())
    ex_target = SanityTarget("trip-booking", "example", tmp_path, (tmp_path,), ())
    file_target = SanityTarget("f.py", "file", tmp_path / "f.py", (), ())

    skip_res = adapter.run_pytest(pkg_target, tmp_path, skip=True)
    assert skip_res.status == CheckStatus.SKIP

    with patch(
        "hexastack_tools.adapters.runners.subprocess_runner._execute_subprocess"
    ) as mock_exec:
        mock_exec.return_value = (0, "10 passed", "", 0.5)
        pkg_res = adapter.run_pytest(pkg_target, tmp_path)
        assert pkg_res.status == CheckStatus.PASS

        ex_res = adapter.run_pytest(ex_target, tmp_path)
        assert ex_res.status == CheckStatus.PASS

        mock_exec.return_value = (1, "1 failed", "Traceback", 0.5)
        file_res = adapter.run_pytest(file_target, tmp_path)
        assert file_res.status == CheckStatus.FAIL
