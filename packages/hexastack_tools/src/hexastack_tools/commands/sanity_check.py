"""Fast scoped sanity check runner for Hexastack packages, examples, and files.

Notes/Architectural Intent:
    Provides a high-velocity inner development loop command that executes the full
    battery of repository quality gates (Ruff lint/format, Ty typechecking, complexipy
    cognitive complexity, __all__ sorting, test parity, and scoped pytest execution)
    against a specific package, example, or modified git diff in seconds.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.commands.all_statements import check_file_all, fix_file_all
from hexastack_tools.commands.test_parity import (
    _check_package_src_symmetry,
    _check_package_test_symmetry,
    check_test_directories_inits,
)
from hexastack_tools.utils.workspace import (
    VALID_EXAMPLES,
    VALID_PACKAGES,
    get_example_directory,
    get_package_directories,
    get_package_directory,
    get_repo_root,
)

__all__ = [
    "CheckResult",
    "find_executable",
    "main",
    "resolve_targets",
    "run_sanity_check",
    "SanityTarget",
]


@dataclass
class SanityTarget:
    """Target component to run sanity checks against.

    Notes/Architectural Intent:
        Encapsulates paths and metadata for packages, examples, or individual source files.
    """

    name: str
    kind: Literal["package", "example", "file"]
    path: Path
    src_paths: list[Path]
    test_paths: list[Path]


@dataclass
class CheckResult:
    """Outcome of an individual sanity check step.

    Notes/Architectural Intent:
        Structured result tracking step status, elapsed duration, and failure diagnostics.
    """

    step_name: str
    target_name: str
    status: Literal["PASS", "FAIL", "SKIP"]
    duration_seconds: float
    details: str
    error_output: str = ""


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
    cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None
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


def _check_ruff(paths: list[Path], target_name: str, fix: bool = False) -> CheckResult:
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
            "Ruff Lint/Format", target_name, "SKIP", 0.0, "No paths found"
        )

    ruff_bin = find_executable("ruff")

    if fix:
        subprocess.run(
            [ruff_bin, "check", "--fix", *path_strs], capture_output=True, check=False
        )
        subprocess.run(
            [ruff_bin, "format", *path_strs], capture_output=True, check=False
        )

    code_chk, out_chk, err_chk, dur_chk = _execute_subprocess(
        [ruff_bin, "check", *path_strs]
    )
    if code_chk != 0:
        return CheckResult(
            "Ruff Lint",
            target_name,
            "FAIL",
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
            "FAIL",
            dur_chk + dur_fmt,
            "Formatting required (run with --fix)",
            error_output=(out_fmt + "\n" + err_fmt).strip(),
        )

    return CheckResult(
        "Ruff Lint/Format",
        target_name,
        "PASS",
        dur_chk + dur_fmt,
        "Code style clean",
    )


def _check_ty(paths: list[Path], target_name: str) -> CheckResult:
    """Run Ty static type checker.

    Args:
        paths: Directory or file paths to typecheck.
        target_name: Human-readable target name.

    Returns:
        CheckResult detailing type diagnostics.
    """
    path_strs = [str(p) for p in paths if p.exists()]
    if not path_strs:
        return CheckResult("Ty Typecheck", target_name, "SKIP", 0.0, "No paths found")

    ty_bin = find_executable("ty")
    code, out, err, duration = _execute_subprocess([ty_bin, "check", *path_strs])

    if code != 0:
        return CheckResult(
            "Ty Typecheck",
            target_name,
            "FAIL",
            duration,
            "Type diagnostics reported",
            error_output=(out + "\n" + err).strip(),
        )

    return CheckResult(
        "Ty Typecheck",
        target_name,
        "PASS",
        duration,
        "All type checks passed",
    )


def _check_complexipy(
    paths: list[Path], target_name: str, max_complexity: int = 25
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
            "Cognitive Complexity", target_name, "SKIP", 0.0, "No paths found"
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

    if violations or (code != 0 and not out.strip()):
        err_msg = "\n".join(violations) if violations else err.strip()
        return CheckResult(
            "Cognitive Complexity",
            target_name,
            "FAIL",
            duration,
            f"{len(violations)} function(s) exceeded threshold {max_complexity}",
            error_output=err_msg,
        )

    return CheckResult(
        "Cognitive Complexity",
        target_name,
        "PASS",
        duration,
        f"All functions <= {max_complexity}",
    )


def _check_all_statements(
    paths: list[Path], target_name: str, fix: bool = False
) -> CheckResult:
    """Verify strictly sorted __all__ statements in Python files.

    Args:
        paths: Target directory or file paths.
        target_name: Human-readable target name.
        fix: Whether to format __all__ before verifying.

    Returns:
        CheckResult detailing __all__ integrity.
    """
    start = time.perf_counter()
    py_files: list[Path] = []
    for p in paths:
        if p.is_file() and p.suffix == ".py":
            py_files.append(p)
        elif p.is_dir():
            py_files.extend(sorted(p.rglob("*.py")))

    if not py_files:
        return CheckResult(
            "__all__ Integrity", target_name, "SKIP", 0.0, "No python files found"
        )

    if fix:
        for f in py_files:
            fix_file_all(f)

    errors: list[str] = []
    for f in py_files:
        errors.extend(check_file_all(f))

    duration = time.perf_counter() - start
    if errors:
        return CheckResult(
            "__all__ Integrity",
            target_name,
            "FAIL",
            duration,
            f"{len(errors)} violation(s) in __all__ declarations",
            error_output="\n".join(errors),
        )

    return CheckResult(
        "__all__ Integrity",
        target_name,
        "PASS",
        duration,
        "Declarations strictly sorted",
    )


def _check_test_parity_step(target: SanityTarget, repo_root: Path) -> CheckResult:
    """Verify 1:1 test symmetry and __init__.py presence.

    Args:
        target: SanityTarget under audit.
        repo_root: Repository root path.

    Returns:
        CheckResult detailing test symmetry.
    """
    start = time.perf_counter()
    if target.kind != "package":
        return CheckResult(
            "Test Parity", target.name, "SKIP", 0.0, "Non-package target"
        )

    pkg_dir = target.path
    src_dir = pkg_dir / "src" / pkg_dir.name
    unit_tests_dir = pkg_dir / "tests" / "unit"

    errors: list[str] = []
    if (pkg_dir / "tests").is_dir():
        errors.extend(check_test_directories_inits(repo_root))

    if src_dir.is_dir() and unit_tests_dir.is_dir():
        errors.extend(
            _check_package_src_symmetry(pkg_dir, repo_root, src_dir, unit_tests_dir)
        )
        errors.extend(
            _check_package_test_symmetry(pkg_dir, repo_root, src_dir, unit_tests_dir)
        )

    duration = time.perf_counter() - start
    if errors:
        return CheckResult(
            "Test Parity",
            target.name,
            "FAIL",
            duration,
            f"{len(errors)} parity violation(s)",
            error_output="\n".join(errors),
        )

    return CheckResult(
        "Test Parity",
        target.name,
        "PASS",
        duration,
        "1:1 test symmetry verified",
    )


def _run_pytest_step(target: SanityTarget, skip_tests: bool = False) -> CheckResult:
    """Run pytest suite scoped to the target component.

    Args:
        target: Target component.
        skip_tests: Whether to skip pytest execution.

    Returns:
        CheckResult with test outcomes.
    """
    if skip_tests:
        return CheckResult(
            "Pytest Suite", target.name, "SKIP", 0.0, "Skipped via --skip-tests"
        )

    test_dirs = [str(p) for p in target.test_paths if p.exists()]
    if not test_dirs:
        return CheckResult("Pytest Suite", target.name, "SKIP", 0.0, "No tests found")

    env = os.environ.copy()
    if target.kind == "example":
        src_path = str((target.path / "src").resolve())
        current_pypath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{src_path}{os.pathsep}{current_pypath}" if current_pypath else src_path
        )

    cmd = [sys.executable, "-m", "pytest", *test_dirs, "-q", "--no-cov"]
    code, out, err, duration = _execute_subprocess(cmd, env=env)

    if code != 0:
        return CheckResult(
            "Pytest Suite",
            target.name,
            "FAIL",
            duration,
            "Tests failed",
            error_output=(out + "\n" + err).strip(),
        )

    return CheckResult(
        "Pytest Suite",
        target.name,
        "PASS",
        duration,
        "All tests passed",
    )


def _detect_git_targets(repo_root: Path) -> list[SanityTarget]:
    """Detect modified packages, examples, or files from git status.

    Args:
        repo_root: Root path of the repository.

    Returns:
        List of detected SanityTarget instances.
    """
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        lines = proc.stdout.splitlines()
    except Exception:
        return []

    changed_files: list[Path] = []
    for line in lines:
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            changed_files.append(repo_root / parts[1])

    packages_touched: set[str] = set()
    examples_touched: set[str] = set()

    for file_path in changed_files:
        try:
            rel = file_path.relative_to(repo_root)
            parts = rel.parts
            if len(parts) >= 2 and parts[0] == "packages":
                packages_touched.add(parts[1])
            elif len(parts) >= 2 and parts[0] == "examples":
                examples_touched.add(parts[1])
        except ValueError:
            continue

    targets: list[SanityTarget] = []
    for pkg in sorted(packages_touched):
        pkg_dir = get_package_directory(pkg, repo_root)
        if pkg_dir.is_dir():
            targets.append(_create_package_target(pkg, pkg_dir))

    for ex in sorted(examples_touched):
        ex_dir = get_example_directory(ex, repo_root)
        if ex_dir.is_dir():
            targets.append(_create_example_target(ex, ex_dir))

    return targets


def _create_package_target(name: str, pkg_dir: Path) -> SanityTarget:
    """Construct SanityTarget for a workspace package."""
    src_dir = pkg_dir / "src"
    tests_dir = pkg_dir / "tests"
    src_paths = [src_dir] if src_dir.is_dir() else [pkg_dir]
    test_paths = [tests_dir] if tests_dir.is_dir() else []
    return SanityTarget(
        name=name,
        kind="package",
        path=pkg_dir,
        src_paths=src_paths,
        test_paths=test_paths,
    )


def _create_example_target(name: str, ex_dir: Path) -> SanityTarget:
    """Construct SanityTarget for an example application."""
    src_dir = ex_dir / "src"
    tests_dir = ex_dir / "tests"
    src_paths = [src_dir] if src_dir.is_dir() else [ex_dir]
    test_paths = [tests_dir] if tests_dir.is_dir() else []
    return SanityTarget(
        name=name,
        kind="example",
        path=ex_dir,
        src_paths=src_paths,
        test_paths=test_paths,
    )


def _resolve_package_targets(
    packages: list[str] | None, repo_root: Path
) -> list[SanityTarget]:
    """Resolve target packages from CLI package arguments.

    Args:
        packages: Package names or 'all'.
        repo_root: Root path of repository.

    Returns:
        List of resolved SanityTarget package targets.
    """
    if not packages:
        return []
    targets: list[SanityTarget] = []
    for pkg in packages:
        if pkg == "all":
            for p in get_package_directories(repo_root):
                targets.append(_create_package_target(p.name, p))
        else:
            pkg_dir = get_package_directory(pkg, repo_root)
            targets.append(_create_package_target(pkg, pkg_dir))
    return targets


def _resolve_example_targets(
    examples: list[str] | None, repo_root: Path
) -> list[SanityTarget]:
    """Resolve example projects from CLI arguments.

    Args:
        examples: Example names.
        repo_root: Root path of repository.

    Returns:
        List of resolved SanityTarget example targets.
    """
    if not examples:
        return []
    return [
        _create_example_target(ex, get_example_directory(ex, repo_root))
        for ex in examples
    ]


def _resolve_file_targets(
    files: list[str] | None, repo_root: Path
) -> list[SanityTarget]:
    """Resolve individual file targets from CLI arguments.

    Args:
        files: Sequence of file or directory path strings.
        repo_root: Root path of repository.

    Returns:
        List of resolved SanityTarget file targets.
    """
    if not files:
        return []
    targets: list[SanityTarget] = []
    for f in files:
        file_p = Path(f) if Path(f).is_absolute() else (repo_root / f)
        if file_p.exists():
            targets.append(
                SanityTarget(
                    name=file_p.name,
                    kind="file",
                    path=file_p,
                    src_paths=[file_p],
                    test_paths=[],
                )
            )
    return targets


def _resolve_fallback_targets(repo_root: Path) -> list[SanityTarget]:
    """Resolve fallback targets via git status or whole-workspace default.

    Args:
        repo_root: Root path of repository.

    Returns:
        List of detected or fallback SanityTarget objects.
    """
    git_targets = _detect_git_targets(repo_root)
    if git_targets:
        return git_targets
    return [
        _create_package_target(p.name, p) for p in get_package_directories(repo_root)
    ]


def resolve_targets(args: argparse.Namespace, repo_root: Path) -> list[SanityTarget]:
    """Resolve target list based on CLI arguments and git diff heuristics.

    Args:
        args: Parsed command-line arguments.
        repo_root: Root path of the repository.

    Returns:
        List of SanityTarget objects to audit.

    Notes/Architectural Intent:
        Resolves explicit package/example/file requests first, falling back to
        git-modified components or all packages if no arguments are provided.
    """
    targets: list[SanityTarget] = []
    targets.extend(_resolve_package_targets(args.packages, repo_root))
    targets.extend(_resolve_example_targets(args.examples, repo_root))
    targets.extend(_resolve_file_targets(args.files, repo_root))

    if args.all_targets and not targets:
        for p in get_package_directories(repo_root):
            targets.append(_create_package_target(p.name, p))

    if not targets:
        targets.extend(_resolve_fallback_targets(repo_root))

    return targets


def run_sanity_check(
    targets: list[SanityTarget],
    repo_root: Path,
    fix: bool = False,
    skip_tests: bool = False,
    max_complexity: int = 25,
    console: Console | None = None,
) -> int:
    """Execute complete sanity check battery across targets and render dashboard.

    Args:
        targets: Sequence of SanityTarget components to audit.
        repo_root: Root path of the repository.
        fix: Whether to auto-format and fix violations.
        skip_tests: Whether to skip pytest suites.
        max_complexity: Cognitive complexity ceiling per function.
        console: Optional Rich Console instance.

    Returns:
        0 if all sanity checks pass, 1 otherwise.

    Notes/Architectural Intent:
        Single-step inner loop runner executing formatting, typecheck, complexity,
        parity, and test verification with rich dashboard output.
    """
    c = console or Console()
    all_results: list[CheckResult] = []

    for target in targets:
        # Check 1: Ruff
        all_results.append(
            _check_ruff(target.src_paths + target.test_paths, target.name, fix=fix)
        )

        # Check 2: Ty Typecheck
        all_results.append(_check_ty(target.src_paths + target.test_paths, target.name))

        # Check 3: Complexipy
        all_results.append(
            _check_complexipy(
                target.src_paths, target.name, max_complexity=max_complexity
            )
        )

        # Check 4: __all__ Integrity
        all_results.append(
            _check_all_statements(target.src_paths, target.name, fix=fix)
        )

        # Check 5: Test Parity (for packages)
        if target.kind == "package":
            all_results.append(_check_test_parity_step(target, repo_root))

        # Check 6: Pytest Suite
        all_results.append(_run_pytest_step(target, skip_tests=skip_tests))

    # Render Dashboard Table
    table = Table(
        title="[bold cyan]Hexastack Scoped Sanity Check Dashboard[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Check", style="cyan", width=22)
    table.add_column("Target", style="bold yellow", width=20)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Duration", justify="right", width=10)
    table.add_column("Details", style="dim")

    has_failure = False
    for r in all_results:
        status_style = (
            "[bold green]✅ PASS[/bold green]"
            if r.status == "PASS"
            else (
                "[bold red]❌ FAIL[/bold red]"
                if r.status == "FAIL"
                else "[dim]⏭️ SKIP[/dim]"
            )
        )
        if r.status == "FAIL":
            has_failure = True

        table.add_row(
            r.step_name,
            r.target_name,
            status_style,
            f"{r.duration_seconds:.2f}s",
            r.details,
        )

    c.print()
    c.print(table)
    c.print()

    # If failures, print diagnostic panels
    if has_failure:
        for r in all_results:
            if r.status == "FAIL" and r.error_output:
                c.print(
                    Panel(
                        r.error_output,
                        title=f"[bold red]❌ {r.step_name} Failure ({r.target_name})[/bold red]",
                        border_style="red",
                    )
                )
        return 1

    total_duration = sum(r.duration_seconds for r in all_results)
    c.print(
        Panel.fit(
            f"[bold green]✨ All {len(all_results)} sanity checks passed in {total_duration:.2f}s![/bold green]",
            border_style="green",
        )
    )
    return 0


def main() -> None:
    """CLI entrypoint for sanity-check."""
    parser = argparse.ArgumentParser(
        description="Fast scoped sanity check runner for Hexastack packages, examples, and files."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Specific files or directories to verify.",
    )
    parser.add_argument(
        "-p",
        "--package",
        dest="packages",
        action="append",
        choices=["all", *VALID_PACKAGES],
        help="Target package(s) (e.g. -p cqrs -p events).",
    )
    parser.add_argument(
        "-e",
        "--example",
        dest="examples",
        action="append",
        choices=VALID_EXAMPLES,
        help="Target example project(s) (e.g. -e trip-booking).",
    )
    parser.add_argument(
        "-a",
        "--all",
        dest="all_targets",
        action="store_true",
        help="Run across all packages unconditionally.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically apply autofixes (ruff --fix, ruff format, fix-all-statements).",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running pytest suites (run static analysis and parity only).",
    )
    parser.add_argument(
        "-mx",
        "--max-complexity",
        type=int,
        default=25,
        help="Cognitive complexity threshold (default: 25).",
    )

    args = parser.parse_args()
    repo_root = get_repo_root()
    targets = resolve_targets(args, repo_root)

    exit_code = run_sanity_check(
        targets=targets,
        repo_root=repo_root,
        fix=args.fix,
        skip_tests=args.skip_tests,
        max_complexity=args.max_complexity,
    )
    sys.exit(exit_code)
