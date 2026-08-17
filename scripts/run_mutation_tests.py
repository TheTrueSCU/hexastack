"""Mutation testing runner script for Hexastack packages using mutmut v2.

Usage:
    # Run a single package
    uv run python scripts/run_mutation_tests.py --package auth
    uv run python scripts/run_mutation_tests.py --package cqrs
    uv run python scripts/run_mutation_tests.py --package core

    # Run all packages sequentially
    uv run python scripts/run_mutation_tests.py --all

    # Inspect a specific surviving mutant diff
    uv run python scripts/run_mutation_tests.py --show 1
"""

import argparse
import subprocess
import sys

from scripts._common import VALID_PACKAGES, get_repo_root

ROOT_DIR = get_repo_root()


def run_command(cmd: list[str]) -> int:
    """Execute a shell command from project root directory."""
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT_DIR, check=False)
    return result.returncode


def run_mutation_test(package: str, path: str | None = None) -> int:
    """Run mutmut against a designated Hexastack package."""
    pkg_clean = package.removeprefix("hexastack_").removeprefix("hexastack-")
    if pkg_clean not in VALID_PACKAGES:
        print(
            f"Error: Unknown package '{package}'. Valid packages: {', '.join(VALID_PACKAGES)}"
        )
        return 1

    pkg_dir = f"packages/hexastack_{pkg_clean}"
    if not (ROOT_DIR / pkg_dir).exists():
        pkg_dir = "packages/hexastack"

    src_path = path or f"{pkg_dir}/src/hexastack_{pkg_clean}"
    tests_path = f"{pkg_dir}/tests/unit"
    pytest_bin = str(ROOT_DIR / ".venv/bin/pytest")

    print("\n========================================================")
    print(f" Starting Mutation Testing: hexastack-{pkg_clean}")
    print(f" Source:    {src_path}")
    print(f" Tests Dir: {tests_path}")
    print(f" Pytest:    {pytest_bin}")
    print("========================================================\n")

    cmd = [
        "uv",
        "run",
        "mutmut",
        "run",
        f"--paths-to-mutate={src_path}",
        f"--tests-dir={tests_path}",
        f'--runner={pytest_bin} {tests_path} -n 0 -x -q --no-cov -o addopts=""',
    ]

    code = run_command(cmd)

    print("\n--- Mutmut Results ---")
    run_command(["uv", "run", "mutmut", "results"])
    return code


def run_all_mutation_tests() -> int:
    """Run mutmut sequentially across all Hexastack packages."""
    print("\n========================================================")
    print(f" Running Mutation Testing Across All {len(VALID_PACKAGES)} Packages")
    print("========================================================\n")

    results: dict[str, int] = {}
    for pkg in VALID_PACKAGES:
        print(f"\n>>> Running mutmut for hexastack-{pkg}...")
        code = run_mutation_test(pkg)
        results[pkg] = code

    print("\n========================================================")
    print(" Mutation Testing Batch Summary")
    print("========================================================")
    for pkg, code in results.items():
        status = (
            "PASSED (0 surviving mutants)"
            if code == 0
            else f"SURVIVORS (exit code {code})"
        )
        print(f"  hexastack-{pkg:<10}: {status}")

    return 0 if all(c == 0 for c in results.values()) else 1


def show_mutant(mutant_id: str) -> int:
    """Display diff for a specific surviving mutant."""
    return run_command(["uv", "run", "mutmut", "show", mutant_id])


def main() -> None:
    """Parse CLI arguments and dispatch mutation test runner."""
    parser = argparse.ArgumentParser(
        description="Hexastack Mutation Testing Runner (mutmut v2)"
    )
    parser.add_argument(
        "-p",
        "--package",
        default=None,
        help="Target package to mutate (e.g. core, cqrs, auth).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run mutation testing sequentially across all packages.",
    )
    parser.add_argument(
        "--path",
        default=None,
        help="Explicit file or directory path to mutate.",
    )
    parser.add_argument(
        "--show",
        default=None,
        help="Inspect a specific mutant diff by ID (e.g. --show 1).",
    )

    args = parser.parse_args()

    if args.show:
        sys.exit(show_mutant(args.show))

    if args.all or args.package == "all":
        sys.exit(run_all_mutation_tests())

    pkg = args.package or "core"
    sys.exit(run_mutation_test(pkg, args.path))


if __name__ == "__main__":
    main()
