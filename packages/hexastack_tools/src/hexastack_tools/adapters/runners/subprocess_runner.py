"""Subprocess-driven tool runner adapter implementing ToolRunnerPort.

Notes/Architectural Intent:
    Executes Ruff, Ty, complexipy, AST __all__ checks, test parity audits,
    and targeted Pytest test suites via portable subprocess invocations.
    Encapsulates CLI arguments, environment configurations, and timing measurement.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

from hexastack_tools.domain.governance import (
    CheckResult,
    CheckStatus,
    SanityTarget,
)
from hexastack_tools.ports.governance import ToolRunnerPort
from hexastack_tools.utils.all_statements import (
    check_file_all,
    fix_file_all,
)
from hexastack_tools.utils.test_parity import check_package_parity

__all__ = [
    "find_executable",
    "SubprocessToolRunnerAdapter",
]


def find_executable(name: str) -> str:
    """Locate executable in virtual environment bin directory or system PATH.

    Args:
        name: Name of the binary executable.

    Returns:
        Absolute or resolved path to the executable string.

    Notes/Architectural Intent:
        Prefers virtualenv binaries matching sys.executable directory over system PATH.
    """
    venv_bin = Path(sys.executable).parent / name
    if venv_bin.is_file():
        return str(venv_bin)
    which_bin = shutil.which(name)
    if which_bin:
        return which_bin
    return name


def _execute_subprocess(
    cmd: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str, float]:
    """Execute command subprocess and measure elapsed duration.

    Args:
        cmd: Command and arguments sequence.
        cwd: Optional working directory.
        env: Optional environment variables dictionary.

    Returns:
        Tuple of (exit_code, stdout, stderr, duration_seconds).
    """
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        duration = time.perf_counter() - start
        return proc.returncode, proc.stdout, proc.stderr, duration
    except Exception as exc:
        duration = time.perf_counter() - start
        return 1, "", str(exc), duration


class SubprocessToolRunnerAdapter(ToolRunnerPort):
    """Concrete adapter executing checks via subprocesses and internal tools."""

    def run_ruff(
        self,
        paths: tuple[Path, ...],
        target_name: str,
        fix: bool = False,
    ) -> CheckResult:
        """Run Ruff linter and formatter check.

        Args:
            paths: Paths to lint and format check.
            target_name: Human-readable target name.
            fix: Whether to automatically fix violations before checking.

        Returns:
            CheckResult detailing status and diagnostics.
        """
        path_strs = [str(p) for p in paths if p.exists()]
        if not path_strs:
            return CheckResult(
                "Ruff Lint/Format", target_name, CheckStatus.SKIP, 0.0, "No paths found"
            )

        ruff_bin = find_executable("ruff")
        if fix:
            subprocess.run(
                [ruff_bin, "check", "--fix", *path_strs],
                capture_output=True,
                check=False,
            )
            subprocess.run(
                [ruff_bin, "format", *path_strs],
                capture_output=True,
                check=False,
            )

        code_chk, out_chk, err_chk, dur_chk = _execute_subprocess(
            [ruff_bin, "check", *path_strs]
        )
        if code_chk != 0:
            return CheckResult(
                "Ruff Lint",
                target_name,
                CheckStatus.FAIL,
                dur_chk,
                "Lint errors detected",
                error_output=(out_chk + "\n" + err_chk).strip(),
            )

        code_fmt, out_fmt, err_fmt, dur_fmt = _execute_subprocess(
            [ruff_bin, "format", "--check", *path_strs]
        )
        if code_fmt != 0:
            return CheckResult(
                "Ruff Format",
                target_name,
                CheckStatus.FAIL,
                dur_chk + dur_fmt,
                "Formatting required (run with --fix)",
                error_output=(out_fmt + "\n" + err_fmt).strip(),
            )

        return CheckResult(
            "Ruff Lint/Format",
            target_name,
            CheckStatus.PASS,
            dur_chk + dur_fmt,
            "Code style clean",
        )

    def run_ty(
        self,
        paths: tuple[Path, ...],
        target_name: str,
    ) -> CheckResult:
        """Run Ty static type checker.

        Args:
            paths: Directory or file paths to typecheck.
            target_name: Human-readable target name.

        Returns:
            CheckResult detailing type diagnostics.
        """
        path_strs = [str(p) for p in paths if p.exists()]
        if not path_strs:
            return CheckResult(
                "Ty Typecheck", target_name, CheckStatus.SKIP, 0.0, "No paths found"
            )

        ty_bin = find_executable("ty")
        code, out, err, duration = _execute_subprocess([ty_bin, "check", *path_strs])

        if code != 0:
            return CheckResult(
                "Ty Typecheck",
                target_name,
                CheckStatus.FAIL,
                duration,
                "Type diagnostics reported",
                error_output=(out + "\n" + err).strip(),
            )

        return CheckResult(
            "Ty Typecheck",
            target_name,
            CheckStatus.PASS,
            duration,
            "All type checks passed",
        )

    def run_complexipy(
        self,
        paths: tuple[Path, ...],
        target_name: str,
        max_complexity: int = 25,
    ) -> CheckResult:
        """Audit cognitive complexity using complexipy.

        Args:
            paths: Paths to inspect.
            target_name: Human-readable target name.
            max_complexity: Maximum allowed cognitive complexity per method.

        Returns:
            CheckResult with complexity status.
        """
        path_strs = [str(p) for p in paths if p.exists()]
        if not path_strs:
            return CheckResult(
                "Cognitive Complexity",
                target_name,
                CheckStatus.SKIP,
                0.0,
                "No paths found",
            )

        cpx_bin = find_executable("complexipy")
        code, out, err, duration = _execute_subprocess(
            [
                cpx_bin,
                *path_strs,
                "--max-complexity-allowed",
                str(max_complexity),
                "--plain",
            ]
        )

        violations: list[str] = []
        for line in out.splitlines():
            parts = line.strip().split()
            if len(parts) >= 3:
                try:
                    score = int(parts[2])
                    if score > max_complexity:
                        violations.append(
                            f"{parts[0]} :: {parts[1]} (score: {score} > {max_complexity})"
                        )
                except ValueError:
                    continue

        if code != 0 or violations:
            details = (
                f"{len(violations)} function(s) exceed complexity {max_complexity}"
            )
            return CheckResult(
                "Cognitive Complexity",
                target_name,
                CheckStatus.FAIL,
                duration,
                details,
                error_output="\n".join(violations) or err.strip(),
            )

        return CheckResult(
            "Cognitive Complexity",
            target_name,
            CheckStatus.PASS,
            duration,
            f"All functions <= {max_complexity}",
        )

    def run_all_statements(
        self,
        paths: tuple[Path, ...],
        target_name: str,
        fix: bool = False,
    ) -> CheckResult:
        """Validate and optionally fix __all__ integrity across python files.

        Args:
            paths: Target paths to inspect.
            target_name: Human-readable target name.
            fix: Whether to automatically sort __all__.

        Returns:
            CheckResult with __all__ sorting outcome.
        """
        start = time.perf_counter()
        py_files: list[Path] = []
        for p in paths:
            if p.is_file() and p.suffix == ".py":
                py_files.append(p)
            elif p.is_dir():
                py_files.extend(p.rglob("*.py"))

        violations: list[str] = []
        for file_path in py_files:
            if fix:
                fix_file_all(file_path)
            viol = check_file_all(file_path)
            if viol:
                violations.extend(viol)

        duration = time.perf_counter() - start
        if violations:
            return CheckResult(
                "__all__ Integrity",
                target_name,
                CheckStatus.FAIL,
                duration,
                f"{len(violations)} __all__ violation(s) found",
                error_output="\n".join(violations),
            )

        return CheckResult(
            "__all__ Integrity",
            target_name,
            CheckStatus.PASS,
            duration,
            "Deduplicated and sorted",
        )

    def run_test_parity(
        self,
        target: SanityTarget,
        repo_root: Path,
    ) -> CheckResult:
        """Validate 1:1 symmetry between src modules and unit test files.

        Args:
            target: Target component to audit.
            repo_root: Repository root path.

        Returns:
            CheckResult with parity diagnostics.
        """
        start = time.perf_counter()
        if target.kind != "package":
            return CheckResult(
                "Test Parity",
                target.name,
                CheckStatus.SKIP,
                0.0,
                "Applicable to packages only",
            )

        all_errors = check_package_parity(target.path, repo_root)
        duration = time.perf_counter() - start

        if all_errors:
            return CheckResult(
                "Test Parity",
                target.name,
                CheckStatus.FAIL,
                duration,
                f"{len(all_errors)} parity error(s)",
                error_output="\n".join(all_errors),
            )

        return CheckResult(
            "Test Parity",
            target.name,
            CheckStatus.PASS,
            duration,
            "1:1 test symmetry verified",
        )

    def run_pytest(
        self,
        target: SanityTarget,
        repo_root: Path,
        skip: bool = False,
    ) -> CheckResult:
        """Execute pytest for targeted component.

        Args:
            target: Target component to test.
            repo_root: Repository root path.
            skip: Whether to skip running tests.

        Returns:
            CheckResult with test outcomes.
        """
        if skip:
            return CheckResult(
                "Pytest Suite",
                target.name,
                CheckStatus.SKIP,
                0.0,
                "Skipped via --skip-tests",
            )

        pytest_bin = find_executable("pytest")
        if target.kind == "package":
            cmd = ["uv", "run", "pytest-run", "-p", target.name]
            code, out, err, dur = _execute_subprocess(cmd, cwd=repo_root)
        elif target.kind == "example":
            cmd = ["uv", "run", "pytest-run", "-e", target.name]
            code, out, err, dur = _execute_subprocess(cmd, cwd=repo_root)
        else:
            cmd = [pytest_bin, str(target.path), "-q"]
            code, out, err, dur = _execute_subprocess(cmd, cwd=repo_root)

        if code != 0:
            return CheckResult(
                "Pytest Suite",
                target.name,
                CheckStatus.FAIL,
                dur,
                "Tests failed",
                error_output=(out + "\n" + err).strip(),
            )

        return CheckResult(
            "Pytest Suite",
            target.name,
            CheckStatus.PASS,
            dur,
            "All tests passed",
        )
