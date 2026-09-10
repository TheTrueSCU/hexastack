"""Pytest test runner and architecture contract generator commands."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from hexastack_tools.utils.workspace import (
    VALID_EXAMPLES,
    VALID_PACKAGES,
    HexastackScriptArgumentParser,
    get_example_directory,
    get_package_directories,
    get_package_directory,
    get_present_layers,
    get_repo_root,
    resolve_affected_packages,
)


def _get_git_changed_files(base_ref: str = "origin/main") -> list[str]:
    """Retrieve list of modified files compared against git base_ref."""
    try:
        res = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        if files:
            return files
    except Exception:
        # Fall back to uncommitted local changes if diff against base_ref fails (e.g. shallow clone)
        pass

    try:
        res = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [line.strip() for line in res.stdout.splitlines() if line.strip()]
    except Exception:
        # If git diff fails entirely (e.g. not in a git working tree), return empty list
        return []


def _setup_example_target(example_name: str, sub_dir: str, root: Path) -> str:
    """Configure sys.path and PYTHONPATH for an example and return its test directory path."""
    ex_dir = get_example_directory(example_name, root)
    src_dir = ex_dir / "src"
    if src_dir.is_dir():
        src_path_str = str(src_dir.resolve())
        if src_path_str not in sys.path:
            sys.path.insert(0, src_path_str)
        current_pypath = os.environ.get("PYTHONPATH", "")
        if src_path_str not in current_pypath.split(os.pathsep):
            os.environ["PYTHONPATH"] = (
                f"{src_path_str}{os.pathsep}{current_pypath}"
                if current_pypath
                else src_path_str
            )
    target = ex_dir / sub_dir
    if target.is_dir():
        return str(target)
    if (ex_dir / "tests").is_dir():
        return str(ex_dir / "tests")
    return str(ex_dir)


def _resolve_package_targets(
    packages: list[str] | None,
    affected: bool,
    sub_dir: str,
    root: Path,
) -> tuple[list[str], set[str] | None]:
    """Resolve target test directory paths for workspace packages."""
    if packages:
        paths = [str(get_package_directory(p, root) / sub_dir) for p in packages]
        return paths, set(packages)

    if affected:
        changed = _get_git_changed_files()
        affected_pkgs = resolve_affected_packages(changed, root)
        if affected_pkgs is not None:
            paths = [
                str(target)
                for p in affected_pkgs
                if (target := get_package_directory(p, root) / sub_dir).is_dir()
            ]
            return paths, affected_pkgs

    paths = [
        str(target)
        for pkg_dir in get_package_directories(root)
        if (target := pkg_dir / sub_dir).is_dir()
    ]
    return paths, None


def _resolve_test_targets(
    packages: list[str] | None,
    examples: list[str] | None,
    affected: bool,
    unit_only: bool,
    properties_only: bool,
    root: Path,
) -> tuple[list[str], set[str] | None]:
    """Resolve target test directory paths and active package set based on CLI flags."""
    if properties_only:
        sub_dir = "tests/properties"
    elif unit_only:
        sub_dir = "tests/unit"
    else:
        sub_dir = "tests"

    if examples:
        paths = [_setup_example_target(e, sub_dir, root) for e in examples]
        return paths, None

    return _resolve_package_targets(packages, affected, sub_dir, root)


def run_main() -> None:
    """CLI entrypoint for pytest-run."""
    parser = argparse.ArgumentParser(description="Run pytest test suite.")
    parser.add_argument(
        "-p", "--package", dest="packages", action="append", choices=VALID_PACKAGES
    )
    parser.add_argument(
        "-e", "--example", dest="examples", action="append", choices=VALID_EXAMPLES
    )
    parser.add_argument(
        "-a",
        "--all",
        dest="all_packages",
        action="store_true",
        help="Run across all workspace packages.",
    )
    parser.add_argument("-A", "--affected", action="store_true")
    parser.add_argument("-U", "--unit", action="store_true")
    parser.add_argument("-P", "--properties", action="store_true")
    parser.add_argument(
        "--with-context",
        action="store_true",
        help="Capture test function contexts in .coverage for Test Impact Analysis and boundary audits (disables xdist).",
    )
    args, unknown = parser.parse_known_args()

    root = get_repo_root()
    test_paths, active_pkgs = _resolve_test_targets(
        packages=args.packages,
        examples=args.examples,
        affected=args.affected,
        unit_only=args.unit,
        properties_only=args.properties,
        root=root,
    )

    cov_args: list[str] = []
    if args.with_context:
        cov_args.extend(["-n", "0", "--cov-context=test"])

    if args.examples:
        # For example runs, disable global fail-under coverage or scope directly
        cov_args.append("--no-cov")
    elif active_pkgs is not None:
        # Dynamically scope coverage only to tested packages
        cov_pkgs = [
            p
            for p in active_pkgs
            if p != "tools" and (get_package_directory(p, root) / "src").is_dir()
        ]
        if cov_pkgs:
            cov_args.append("--cov-reset")
            for p in cov_pkgs:
                pkg_src = get_package_directory(p, root) / "src"
                cov_args.append(f"--cov={pkg_src}")
        else:
            # Only test tooling/non-covered packages: disable coverage fail-under
            cov_args.append("--no-cov")

    call_args = test_paths + cov_args + (unknown or [])
    res = subprocess.run([sys.executable, "-m", "pytest", *call_args])
    sys.exit(res.returncode)


def archon_generate_main() -> None:
    """CLI entrypoint for pytest-archon-generate."""
    parser = HexastackScriptArgumentParser(
        description="Generate pytest-archon boundary tests for packages."
    )
    args = parser.parse_args()

    root = get_repo_root()
    packages = (
        [get_package_directory(p, root) for p in args.packages]
        if args.packages
        else get_package_directories(root)
    )

    for pkg_path in packages:
        pkg_name = pkg_path.name
        if not get_present_layers(pkg_path):
            continue

        test_lines = [
            f'"""Hexagonal architecture boundary tests for {pkg_name}."""',
            "",
            "from hexastack_core.testing import assert_clean_architecture",
            "",
            "",
            f"def test_{pkg_name.replace('-', '_')}_clean_architecture():",
            f'    """Assert {pkg_name} strictly complies with Hexagonal layer isolation."""',
            f'    assert_clean_architecture("{pkg_name.replace("-", "_")}")',
            "",
        ]
        arch_dir = pkg_path / "tests" / "architecture"
        arch_dir.mkdir(parents=True, exist_ok=True)
        (arch_dir / "test_hexagonal_boundaries.py").write_text(
            "\n".join(test_lines).strip() + "\n"
        )


__all__ = [
    "archon_generate_main",
    "run_main",
]
