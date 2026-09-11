"""CLI Driving Adapter for Scoped Sanity Check Runner.

Notes/Architectural Intent:
    Acts strictly as a driving adapter: parses CLI arguments, builds domain
    commands, dispatches them through the CommandBusPort, and forwards reports
    to the GovernancePresenterPort.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from rich.console import Console

from hexastack_cqrs.ports.buses import CommandBusPort
from hexastack_tools.adapters.presenters.governance import (
    RichGovernancePresenterAdapter,
)
from hexastack_tools.domain.governance import (
    CheckResult,
    RunSanityCheckCommand,
    SanityCheckReport,
    SanityTarget,
)
from hexastack_tools.infra.bootstrap import create_governance_bus
from hexastack_tools.ports.governance import (
    GovernancePresenterPort,
    ToolRunnerPort,
)
from hexastack_tools.utils.workspace import (
    get_example_directory,
    get_package_directories,
    get_package_directory,
    get_repo_root,
)

__all__ = [
    "CheckResult",
    "main",
    "resolve_targets",
    "run_sanity_check",
    "SanityTarget",
]


def _create_package_target(name: str, pkg_dir: Path) -> SanityTarget:
    """Construct SanityTarget for a package directory."""
    src_dir = pkg_dir / "src"
    test_dir = pkg_dir / "tests"
    return SanityTarget(
        name=name,
        kind="package",
        path=pkg_dir,
        src_paths=(src_dir,) if src_dir.is_dir() else (pkg_dir,),
        test_paths=(test_dir,) if test_dir.is_dir() else (),
    )


def _create_example_target(name: str, ex_dir: Path) -> SanityTarget:
    """Construct SanityTarget for an example directory."""
    src_dir = ex_dir / "src"
    test_dir = ex_dir / "tests"
    return SanityTarget(
        name=name,
        kind="example",
        path=ex_dir,
        src_paths=(src_dir,) if src_dir.is_dir() else (ex_dir,),
        test_paths=(test_dir,) if test_dir.is_dir() else (),
    )


def _detect_git_targets(repo_root: Path) -> list[SanityTarget]:
    """Inspect git status for modified packages and examples."""
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return []

    touched_pkgs: set[str] = set()
    touched_examples: set[str] = set()

    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        rel_path = line[3:].strip()
        parts = Path(rel_path).parts
        if len(parts) >= 2 and parts[0] == "packages":
            touched_pkgs.add(parts[1])
        elif len(parts) >= 2 and parts[0] == "examples":
            touched_examples.add(parts[1])

    targets: list[SanityTarget] = []
    for pkg in sorted(touched_pkgs):
        try:
            pkg_dir = get_package_directory(pkg, repo_root)
            if pkg_dir.is_dir():
                targets.append(_create_package_target(pkg, pkg_dir))
        except RuntimeError:
            continue

    for ex in sorted(touched_examples):
        try:
            ex_dir = get_example_directory(ex, repo_root)
            if ex_dir.is_dir():
                targets.append(_create_example_target(ex, ex_dir))
        except RuntimeError:
            continue

    return targets


def _resolve_package_targets(
    packages: list[str] | None, repo_root: Path
) -> list[SanityTarget]:
    """Resolve target packages from CLI package arguments."""
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
    """Resolve example projects from CLI arguments."""
    if not examples:
        return []
    return [
        _create_example_target(ex, get_example_directory(ex, repo_root))
        for ex in examples
    ]


def _resolve_file_targets(
    files: list[str] | None, repo_root: Path
) -> list[SanityTarget]:
    """Resolve individual file targets from CLI arguments."""
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
                    src_paths=(file_p,),
                    test_paths=(),
                )
            )
    return targets


def _resolve_fallback_targets(repo_root: Path) -> list[SanityTarget]:
    """Resolve fallback targets via git status or whole-workspace default."""
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
    bus: CommandBusPort | None = None,
    presenter: GovernancePresenterPort | None = None,
    runner: ToolRunnerPort | None = None,
) -> int:
    """Execute complete sanity check battery across targets and render dashboard.

    Args:
        targets: Sequence of SanityTarget components to audit.
        repo_root: Root path of the repository.
        fix: Whether to auto-format and fix violations.
        skip_tests: Whether to skip pytest suites.
        max_complexity: Cognitive complexity ceiling per function.
        console: Optional Rich Console instance.
        bus: Optional CommandBusPort instance for CQRS dispatch.
        presenter: Optional GovernancePresenterPort for report output.
        runner: Optional ToolRunnerPort adapter.

    Returns:
        0 if all sanity checks pass, 1 otherwise.

    Notes/Architectural Intent:
        Dogfoods Hexastack CQRS: builds a RunSanityCheckCommand and dispatches
        through the CommandBusPort, delegating presentation to GovernancePresenterPort.
    """
    actual_bus = bus or create_governance_bus(runner=runner)
    actual_presenter = presenter or RichGovernancePresenterAdapter(console=console)

    cmd = RunSanityCheckCommand(
        targets=tuple(targets),
        repo_root=repo_root,
        fix=fix,
        skip_tests=skip_tests,
        max_complexity=max_complexity,
    )

    report: SanityCheckReport = actual_bus.dispatch(cmd)
    return actual_presenter.present_sanity_dashboard(report)


def _build_parser() -> argparse.ArgumentParser:
    """Construct argument parser with target choices and execution flags."""
    parser = argparse.ArgumentParser(
        prog="sanity-check",
        description="Fast scoped sanity check runner for Hexastack packages, examples, and files.",
    )
    valid_packages = [
        "all",
        "ai",
        "auth",
        "cli",
        "core",
        "cqrs",
        "db",
        "events",
        "fastapi",
        "flags",
        "graphql",
        "grpc",
        "hexastack",
        "hexastack_ai",
        "hexastack_auth",
        "hexastack_cli",
        "hexastack_core",
        "hexastack_cqrs",
        "hexastack_db",
        "hexastack_events",
        "hexastack_fastapi",
        "hexastack_flags",
        "hexastack_graphql",
        "hexastack_grpc",
        "hexastack_logging",
        "hexastack_mcp",
        "hexastack_otel",
        "hexastack_tools",
        "hexastack_ui",
        "logging",
        "mcp",
        "otel",
        "tools",
        "ui",
    ]
    valid_examples = [
        "financial-ledger",
        "financial_ledger",
        "todo-app",
        "todo_app",
        "trip-booking",
        "trip_booking",
    ]
    parser.add_argument(
        "-p",
        "--package",
        dest="packages",
        action="append",
        choices=valid_packages,
        help="Target package(s) (e.g. -p cqrs -p events).",
    )
    parser.add_argument(
        "-e",
        "--example",
        dest="examples",
        action="append",
        choices=valid_examples,
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
        dest="fix",
        action="store_true",
        help="Automatically apply autofixes (ruff --fix, ruff format, fix-all-statements).",
    )
    parser.add_argument(
        "--skip-tests",
        dest="skip_tests",
        action="store_true",
        help="Skip running pytest suites (run static analysis and parity only).",
    )
    parser.add_argument(
        "-mx",
        "--max-complexity",
        dest="max_complexity",
        type=int,
        default=25,
        help="Cognitive complexity threshold (default: 25).",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Specific files or directories to verify.",
    )
    return parser


def main() -> None:
    """CLI entrypoint for sanity-check."""
    parser = _build_parser()
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


if __name__ == "__main__":
    main()
