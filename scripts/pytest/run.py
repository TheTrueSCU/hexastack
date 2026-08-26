"""Pytest test runner and affected-package test resolver for Hexastack.

Notes/Architectural Intent:
    Invokes pytest directly in-process via `pytest.main()`, supporting:
    1. Running full monorepo test suite with standard flags.
    2. Impact-driven selective testing via `--affected` / `-A` (inspecting git diff).
    3. Targeted package testing via `--package` / `-p`.
    4. Automatically scoping test discovery and coverage reporting.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pytest

from scripts._common import (
    VALID_PACKAGES,
    get_package_directory,
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
        pass

    # Fallback to local unstaged/staged diff
    try:
        res = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [line.strip() for line in res.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def build_pytest_args(
    target_pkgs: set[str] | None,
    repo_root: Path,
    extra_pytest_args: list[str],
    properties_only: bool = False,
    unit_only: bool = False,
) -> list[str]:
    """Construct pytest command arguments targeting specific packages."""
    pytest_args: list[str] = ["--import-mode=importlib"]

    # If target_pkgs is None, run all packages
    if target_pkgs is None:
        target_dirs = [get_package_directory(p, repo_root) for p in VALID_PACKAGES]
    else:
        target_dirs = [get_package_directory(p, repo_root) for p in target_pkgs]

    if not target_dirs:
        return []

    test_paths: list[str] = []
    for pkg_dir in target_dirs:
        tests_dir = pkg_dir / "tests"
        if not tests_dir.is_dir():
            continue

        if properties_only:
            prop_dir = tests_dir / "properties"
            if prop_dir.is_dir():
                test_paths.append(str(prop_dir))
        elif unit_only:
            test_paths.append(str(tests_dir))
            pytest_args.append(f"--ignore-glob={pkg_dir}/tests/properties/*")
        else:
            test_paths.append(str(tests_dir))

    if not test_paths:
        return []

    pytest_args.extend(test_paths)
    pytest_args.extend(extra_pytest_args)
    return pytest_args


def main(cli_args: list[str] | None = None) -> int:
    """CLI entrypoint for running pytest across full workspace or affected packages."""
    parser = argparse.ArgumentParser(
        description="Hexastack Pytest Runner with Affected Package Resolution."
    )
    parser.add_argument(
        "-A",
        "--affected",
        action="store_true",
        help="Run tests only for affected packages based on git diff.",
    )
    parser.add_argument(
        "--base-ref",
        default="origin/main",
        help="Git base reference for diffing affected files (default: origin/main).",
    )
    parser.add_argument(
        "-p",
        "--package",
        dest="packages",
        action="append",
        choices=VALID_PACKAGES,
        help="Target specific package(s) (e.g. -p fastapi -p core).",
    )
    parser.add_argument(
        "-P",
        "--properties",
        action="store_true",
        help="Target only properties/fuzzing test suites.",
    )
    parser.add_argument(
        "-U",
        "--unit",
        action="store_true",
        help="Exclude properties/fuzzing test suites (standard unit/integration only).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List affected packages and test paths without running pytest.",
    )
    args, extra_args = parser.parse_known_args(cli_args)
    repo_root = get_repo_root()

    target_pkgs: set[str] | None = None

    if args.packages:
        target_pkgs = set(args.packages)
    elif args.affected:
        changed_files = _get_git_changed_files(args.base_ref)
        affected = resolve_affected_packages(changed_files, repo_root)
        if affected is None:
            # Root changes -> all packages affected
            target_pkgs = None
        elif not affected:
            print("✨ No code packages affected by current changeset. 0 tests needed.")
            return 0
        else:
            target_pkgs = affected

    if args.list:
        if target_pkgs is None:
            print("Affected packages: [ALL] (Full workspace suite)")
        else:
            print(
                f"Affected packages ({len(target_pkgs)}): {', '.join(sorted(target_pkgs))}"
            )
        return 0

    forwarded_args = list(extra_args)
    # Strip leading '--' if passed to separate args
    if forwarded_args and forwarded_args[0] == "--":
        forwarded_args = forwarded_args[1:]

    pytest_cmd_args = build_pytest_args(
        target_pkgs=target_pkgs,
        repo_root=repo_root,
        extra_pytest_args=forwarded_args,
        properties_only=args.properties,
        unit_only=args.unit,
    )

    if not pytest_cmd_args:
        print("ℹ️ No test directories found for target package selection.")
        return 0

    print(f"🚀 Running pytest with {len(pytest_cmd_args)} arguments...")
    exit_code = pytest.main(pytest_cmd_args)
    return int(exit_code)


if __name__ == "__main__":
    sys.exit(main())
