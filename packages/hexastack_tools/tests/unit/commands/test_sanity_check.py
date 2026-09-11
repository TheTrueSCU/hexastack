"""Unit tests for the scoped sanity check command runner.

Notes/Architectural Intent:
    Validates target resolution (package, example, file, git heuristics),
    subprocess execution wrapping, static analysis verification steps,
    and Rich dashboard rendering.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from rich.console import Console

from hexastack_tools.commands.sanity_check import (
    CheckResult,
    SanityTarget,
    _check_complexipy,
    _check_ruff,
    _check_test_parity_step,
    _check_ty,
    _detect_git_targets,
    _run_pytest_step,
    find_executable,
    resolve_targets,
    run_sanity_check,
)


def test_sanity_target_and_check_result_structures(tmp_path: Path) -> None:
    """Verify SanityTarget and CheckResult dataclass field initializations."""
    target = SanityTarget(
        name="test-pkg",
        kind="package",
        path=tmp_path,
        src_paths=[tmp_path / "src"],
        test_paths=[tmp_path / "tests"],
    )
    assert target.name == "test-pkg"
    assert target.kind == "package"
    assert target.path == tmp_path

    result = CheckResult(
        step_name="TestStep",
        target_name="test-pkg",
        status="PASS",
        duration_seconds=0.42,
        details="Success details",
    )
    assert result.step_name == "TestStep"
    assert result.status == "PASS"
    assert result.duration_seconds == 0.42


def test_find_executable_fallback() -> None:
    """Verify find_executable finds system or python binary."""
    exe = find_executable("python3")
    assert exe is not None
    assert len(exe) > 0


def test_resolve_targets_package(tmp_path: Path) -> None:
    """Verify CLI argument resolution for explicit packages."""
    args = argparse.Namespace(
        packages=["cqrs"],
        examples=None,
        files=None,
        all_targets=False,
    )
    targets = resolve_targets(args, tmp_path)
    assert len(targets) == 1
    t = targets[0]
    assert t.name == "cqrs"
    assert t.kind == "package"


def test_resolve_targets_example(tmp_path: Path) -> None:
    """Verify CLI argument resolution for explicit examples."""
    args = argparse.Namespace(
        packages=None,
        examples=["trip-booking"],
        files=None,
        all_targets=False,
    )
    targets = resolve_targets(args, tmp_path)
    assert len(targets) == 1
    t = targets[0]
    assert t.name == "trip-booking"
    assert t.kind == "example"


def test_resolve_targets_explicit_file(tmp_path: Path) -> None:
    """Verify CLI argument resolution for explicit file paths."""
    sample_file = tmp_path / "mod.py"
    sample_file.write_text("x = 1\n", encoding="utf-8")

    args = argparse.Namespace(
        packages=None,
        examples=None,
        files=[str(sample_file)],
        all_targets=False,
    )
    targets = resolve_targets(args, tmp_path)
    assert len(targets) == 1
    t = targets[0]
    assert t.name == "mod.py"
    assert t.kind == "file"


def test_check_ruff_success(tmp_path: Path) -> None:
    """Verify _check_ruff reports PASS when ruff checks exit with code 0."""
    py_file = tmp_path / "code.py"
    py_file.write_text("a = 1\n", encoding="utf-8")

    with patch(
        "hexastack_tools.commands.sanity_check._execute_subprocess"
    ) as mock_exec:
        mock_exec.return_value = (0, "", "", 0.1)
        res = _check_ruff([py_file], "test-target", fix=False)
        assert res.status == "PASS"
        assert res.step_name == "Ruff Lint/Format"


def test_check_ruff_failure(tmp_path: Path) -> None:
    """Verify _check_ruff reports FAIL when ruff check detects violations."""
    py_file = tmp_path / "code.py"
    py_file.write_text("a = 1\n", encoding="utf-8")

    with patch(
        "hexastack_tools.commands.sanity_check._execute_subprocess"
    ) as mock_exec:
        mock_exec.return_value = (1, "E501 line too long", "", 0.1)
        res = _check_ruff([py_file], "test-target", fix=False)
        assert res.status == "FAIL"
        assert "Lint errors detected" in res.details


def test_check_ty_success_and_failure(tmp_path: Path) -> None:
    """Verify _check_ty reports PASS and FAIL based on ty execution returncode."""
    py_file = tmp_path / "code.py"
    py_file.write_text("a: int = 1\n", encoding="utf-8")

    with patch(
        "hexastack_tools.commands.sanity_check._execute_subprocess"
    ) as mock_exec:
        mock_exec.return_value = (0, "All checks passed!", "", 0.2)
        res_pass = _check_ty([py_file], "test-target")
        assert res_pass.status == "PASS"

        mock_exec.return_value = (1, "Type error on line 1", "", 0.2)
        res_fail = _check_ty([py_file], "test-target")
        assert res_fail.status == "FAIL"
        assert "Type diagnostics reported" in res_fail.details


def test_check_complexipy_violations(tmp_path: Path) -> None:
    """Verify _check_complexipy identifies and reports functions exceeding threshold."""
    py_file = tmp_path / "code.py"
    py_file.write_text("def f(): pass\n", encoding="utf-8")

    cpx_output = "src/pkg/mod.py heavy_function 35\nsrc/pkg/mod.py simple_function 4\n"
    with patch(
        "hexastack_tools.commands.sanity_check._execute_subprocess"
    ) as mock_exec:
        mock_exec.return_value = (0, cpx_output, "", 0.15)
        res = _check_complexipy([py_file], "test-target", max_complexity=25)
        assert res.status == "FAIL"
        assert "exceeded threshold 25" in res.details
        assert "heavy_function" in res.error_output


def test_check_test_parity_step_package(tmp_path: Path) -> None:
    """Verify _check_test_parity_step detects missing tests or inits."""
    pkg_dir = tmp_path / "packages" / "test_pkg"
    src_dir = pkg_dir / "src" / "test_pkg"
    tests_dir = pkg_dir / "tests" / "unit"
    src_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    target = SanityTarget(
        name="test_pkg",
        kind="package",
        path=pkg_dir,
        src_paths=[src_dir],
        test_paths=[tests_dir],
    )

    with (
        patch(
            "hexastack_tools.commands.sanity_check.check_test_directories_inits",
            return_value=[],
        ),
        patch(
            "hexastack_tools.commands.sanity_check._check_package_src_symmetry",
            return_value=["missing test"],
        ),
        patch(
            "hexastack_tools.commands.sanity_check._check_package_test_symmetry",
            return_value=[],
        ),
    ):
        res = _check_test_parity_step(target, tmp_path)
        assert res.status == "FAIL"
        assert "parity violation" in res.details


def test_run_pytest_step_skip_and_exec(tmp_path: Path) -> None:
    """Verify _run_pytest_step honors skip flag and delegates execution."""
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    target = SanityTarget(
        name="test_pkg",
        kind="package",
        path=tmp_path,
        src_paths=[],
        test_paths=[test_dir],
    )

    # 1. Skipped
    res_skip = _run_pytest_step(target, skip_tests=True)
    assert res_skip.status == "SKIP"

    # 2. Executed
    with patch(
        "hexastack_tools.commands.sanity_check._execute_subprocess"
    ) as mock_exec:
        mock_exec.return_value = (0, "10 passed in 0.5s", "", 0.5)
        res_exec = _run_pytest_step(target, skip_tests=False)
        assert res_exec.status == "PASS"


def test_detect_git_targets(tmp_path: Path) -> None:
    """Verify _detect_git_targets parses git status output to identify touched packages."""
    git_stdout = (
        " M packages/hexastack_cqrs/src/mod.py\n?? examples/trip-booking/src/app.py\n"
    )
    mock_proc = MagicMock(stdout=git_stdout)

    with (
        patch("subprocess.run", return_value=mock_proc),
        patch(
            "hexastack_tools.commands.sanity_check.get_package_directory",
            return_value=tmp_path,
        ),
        patch(
            "hexastack_tools.commands.sanity_check.get_example_directory",
            return_value=tmp_path,
        ),
        patch("pathlib.Path.is_dir", return_value=True),
    ):
        targets = _detect_git_targets(tmp_path)
        names = {t.name for t in targets}
        assert "hexastack_cqrs" in names
        assert "trip-booking" in names


def test_run_sanity_check_rendering(tmp_path: Path) -> None:
    """Verify run_sanity_check renders results to Console and computes exit codes."""
    target = SanityTarget(
        name="dummy-pkg",
        kind="package",
        path=tmp_path,
        src_paths=[],
        test_paths=[],
    )
    console = Console(record=True)

    with (
        patch("hexastack_tools.commands.sanity_check._check_ruff") as m_ruff,
        patch("hexastack_tools.commands.sanity_check._check_ty") as m_ty,
        patch("hexastack_tools.commands.sanity_check._check_complexipy") as m_cpx,
        patch("hexastack_tools.commands.sanity_check._check_all_statements") as m_all,
        patch("hexastack_tools.commands.sanity_check._check_test_parity_step") as m_par,
        patch("hexastack_tools.commands.sanity_check._run_pytest_step") as m_pyt,
    ):
        pass_res = CheckResult("Step", "dummy-pkg", "PASS", 0.05, "OK")
        m_ruff.return_value = pass_res
        m_ty.return_value = pass_res
        m_cpx.return_value = pass_res
        m_all.return_value = pass_res
        m_par.return_value = pass_res
        m_pyt.return_value = pass_res

        code_pass = run_sanity_check([target], tmp_path, console=console)
        assert code_pass == 0

        fail_res = CheckResult(
            "Step", "dummy-pkg", "FAIL", 0.05, "ERR", error_output="Details"
        )
        m_ruff.return_value = fail_res
        code_fail = run_sanity_check([target], tmp_path, console=console)
        assert code_fail == 1
