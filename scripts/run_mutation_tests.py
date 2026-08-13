#!/usr/bin/env python3
"""Mutation testing runner script for Hexastack packages using mutmut v2.

Usage:
    uv run python scripts/run_mutation_tests.py --package auth
    uv run python scripts/run_mutation_tests.py --package cqrs
    uv run python scripts/run_mutation_tests.py --package core
    uv run python scripts/run_mutation_tests.py --show 1
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

VALID_PACKAGES = [
    "ai",
    "auth",
    "cli",
    "core",
    "cqrs",
    "db",
    "events",
    "fastapi",
    "graphql",
    "grpc",
    "logging",
    "mcp",
    "otel",
]


def run_command(cmd: list[str]) -> int:
    """Execute a shell command from project root directory."""
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT_DIR)
    return result.returncode


def run_mutation_test(package: str, path: str | None = None) -> int:
    """Run mutmut against a designated Hexastack package."""
    pkg_clean = package.removeprefix("hexastack_").removeprefix("hexastack-")
    if pkg_clean not in VALID_PACKAGES:
        print(
            f"Error: Unknown package '{package}'. Valid packages: {', '.join(VALID_PACKAGES)}"
        )
        return 1

    pkg_dir = ROOT_DIR / f"packages/hexastack_{pkg_clean}"
    if not pkg_dir.exists():
        pkg_dir = ROOT_DIR / "packages/hexastack"

    src_path = path or str(pkg_dir / f"src/hexastack_{pkg_clean}")
    tests_path = str(pkg_dir / "tests/unit")

    print("\n========================================================")
    print(f" Starting Mutation Testing: hexastack-{pkg_clean}")
    print(f" Source:    {src_path}")
    print(f" Tests Dir: {tests_path}")
    print("========================================================\n")

    cmd = [
        "uv",
        "run",
        "mutmut",
        "run",
        f"--paths-to-mutate={src_path}",
        f"--tests-dir={tests_path}",
        f"--runner=pytest {tests_path} -x -q --no-cov",
    ]

    code = run_command(cmd)

    print("\n--- Mutmut Results ---")
    run_command(["uv", "run", "mutmut", "results"])
    return code


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
        default="auth",
        help="Target package to mutate (default: auth).",
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

    sys.exit(run_mutation_test(args.package, args.path))


if __name__ == "__main__":
    main()
