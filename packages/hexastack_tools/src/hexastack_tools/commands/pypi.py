"""PyPI Monorepo Distribution Builder, Checker, and Smart Publisher.

Notes/Architectural Intent:
    CLI driving adapter delegating PyPI checks, builds, publishing, and reproducible
    audits to the Hexastack CQRS governance bus and multi-format presenters.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console

from hexastack_tools.adapters.presenters.pypi import create_pypi_presenter
from hexastack_tools.adapters.runners.pypi_runner import SubprocessPyPiRunnerAdapter
from hexastack_tools.domain.pypi import (
    BuildPackagesCommand,
    CheckPyPiReleasesCommand,
    PackageMetadata,
    PublishPackagesCommand,
    VerifyReproducibleBuildCommand,
)
from hexastack_tools.infra.bootstrap import create_governance_bus
from hexastack_tools.infra.handlers.pypi import discover_workspace_packages
from hexastack_tools.ports.pypi import PyPiClientPort

console = Console()

__all__ = [
    "build_all_packages",
    "build_main",
    "check_main",
    "check_pypi_version_exists",
    "get_workspace_packages_metadata",
    "PackageMetadata",
    "publish_main",
    "publish_packages",
    "reproducible_main",
    "verify_reproducible_builds",
]


class _DelegatingPyPiClient(PyPiClientPort):
    """Client adapter delegating version checks to module-level check_pypi_version_exists."""

    def __init__(self, runner: SubprocessPyPiRunnerAdapter) -> None:
        self._runner = runner

    def check_version_exists(self, package_name: str, version: str) -> bool:
        return check_pypi_version_exists(package_name, version)

    def build_package(
        self,
        package_name: str,
        out_dir: Path,
        env: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
        return self._runner.build_package(package_name, out_dir, env=env)

    def publish_package(
        self,
        files: list[Path],
        token: str | None = None,
    ) -> tuple[bool, str]:
        return self._runner.publish_package(files, token=token)

    def get_git_commit_epoch(self) -> str | None:
        return self._runner.get_git_commit_epoch()


def get_workspace_packages_metadata() -> list[PackageMetadata]:
    """Discover all packages in the workspace and extract their name and version."""
    return discover_workspace_packages()


def check_pypi_version_exists(package_name: str, version: str) -> bool:
    """Check if a specific package version is already released on PyPI."""
    runner = SubprocessPyPiRunnerAdapter()
    return runner.check_version_exists(package_name, version)


def build_all_packages(
    out_dir: Path | None = None,
    package_name: str | None = None,
    format_name: str = "rich",
) -> int:
    """Build distribution artifacts for all workspace packages."""
    bus = create_governance_bus()
    report = bus.dispatch(
        BuildPackagesCommand(target_dist=out_dir, package_name=package_name)
    )
    if not report.results:
        return 1
    presenter = create_pypi_presenter(format_name, console=console)
    return presenter.present_build(report)


def build_main() -> None:
    """CLI entrypoint for pypi-build."""
    parser = argparse.ArgumentParser(
        description="Build distribution packages (wheels and sdists) for all workspace packages."
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Target directory for generated distribution packages (default: dist/)",
    )
    parser.add_argument(
        "--reproducible-check",
        action="store_true",
        help="Audit build determinism and verify byte-for-byte reproducibility before building",
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        default="rich",
        choices=["rich", "json", "markdown"],
        help="Output format: rich (tables), json, markdown.",
    )
    args = parser.parse_args()
    if args.reproducible_check:
        repro_rc = verify_reproducible_builds(format_name=args.format)
        if repro_rc != 0:
            sys.exit(repro_rc)
    if args.format != "rich":
        sys.exit(build_all_packages(out_dir=args.out_dir, format_name=args.format))
    sys.exit(build_all_packages(out_dir=args.out_dir))


def check_main() -> None:
    """CLI entrypoint for pypi-check."""
    parser = argparse.ArgumentParser(
        description="Verify package release version availability against PyPI index."
    )
    parser.add_argument(
        "-p",
        "--package",
        type=str,
        default=None,
        help="Specific package name to check (default: all workspace packages)",
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        default="rich",
        choices=["rich", "json", "markdown"],
        help="Output format: rich (tables), json, markdown.",
    )
    args = parser.parse_args()

    client = _DelegatingPyPiClient(SubprocessPyPiRunnerAdapter())
    bus = create_governance_bus(pypi_client=client)
    report = bus.dispatch(CheckPyPiReleasesCommand(package_name=args.package))
    presenter = create_pypi_presenter(args.format, console=console)
    presenter.present_check(report)


def publish_packages(
    packages_to_publish: list[PackageMetadata] | None = None,
    dist_dir: Path | None = None,
    token: str | None = None,
    delay: float = 3.0,
    skip_existing: bool = True,
    format_name: str = "rich",
) -> int:
    """Publish built package distributions to PyPI with smart duplicate skipping and rate-limit detection."""
    packages = packages_to_publish or get_workspace_packages_metadata()
    if not packages:
        console.print("[bold yellow]No workspace packages discovered.[/bold yellow]")
        return 0

    client = _DelegatingPyPiClient(SubprocessPyPiRunnerAdapter())
    bus = create_governance_bus(pypi_client=client)
    cmd = PublishPackagesCommand(
        dist_dir=dist_dir,
        token=token,
        delay=delay,
        skip_existing=skip_existing,
        packages=tuple(packages),
    )
    report = bus.dispatch(cmd)
    presenter = create_pypi_presenter(format_name, console=console)
    return presenter.present_publish(report)


def publish_main() -> None:
    """CLI entrypoint for pypi-publish."""
    parser = argparse.ArgumentParser(
        description="Build and publish workspace packages to PyPI, skipping already published releases."
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=None,
        help="Directory containing pre-built distribution packages (default: dist/)",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        default=True,
        help="Automatically build distribution packages before publishing (default: True)",
    )
    parser.add_argument(
        "--no-build",
        dest="build",
        action="store_false",
        help="Skip building and publish existing artifacts in dist/",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="PyPI upload token (defaults to UV_PUBLISH_TOKEN or PYPI_TOKEN env vars)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between package uploads (default: 2.0s)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Attempt upload even if version is already marked as published on PyPI",
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        default="rich",
        choices=["rich", "json", "markdown"],
        help="Output format: rich (tables), json, markdown.",
    )
    args = parser.parse_args()

    if args.build:
        build_rc = build_all_packages(out_dir=args.dist_dir, format_name=args.format)
        if build_rc != 0:
            console.print(
                "[bold red]Failed to build all packages. Aborting publish.[/bold red]"
            )
            sys.exit(build_rc)

    sys.exit(
        publish_packages(
            dist_dir=args.dist_dir,
            token=args.token,
            delay=args.delay,
            skip_existing=not args.force,
            format_name=args.format,
        )
    )


def verify_reproducible_builds(
    packages_to_check: list[PackageMetadata] | None = None,
    source_date_epoch: str | None = None,
    format_name: str = "rich",
) -> int:
    """Verify that packages produce byte-for-byte reproducible wheel and sdist distributions."""
    packages = packages_to_check or get_workspace_packages_metadata()
    if not packages:
        return 1

    bus = create_governance_bus()
    cmd = VerifyReproducibleBuildCommand(
        packages=tuple(packages),
        source_date_epoch=source_date_epoch,
    )
    report = bus.dispatch(cmd)
    presenter = create_pypi_presenter(format_name, console=console)
    return presenter.present_reproducible(report)


def reproducible_main() -> None:
    """CLI entrypoint for pypi-reproducible-check."""
    parser = argparse.ArgumentParser(
        description="Verify byte-for-byte reproducible builds across workspace packages."
    )
    parser.add_argument(
        "-p",
        "--package",
        type=str,
        default=None,
        help="Specific package name to verify (default: all packages)",
    )
    parser.add_argument(
        "--epoch",
        type=str,
        default=None,
        help="Custom SOURCE_DATE_EPOCH timestamp (default: git commit timestamp)",
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        default="rich",
        choices=["rich", "json", "markdown"],
        help="Output format: rich (tables), json, markdown.",
    )
    args = parser.parse_args()

    packages = get_workspace_packages_metadata()
    if args.package:
        packages = [p for p in packages if p.name == args.package]
        if not packages:
            console.print(
                f"[bold red]Package '{args.package}' not found in workspace.[/bold red]"
            )
            sys.exit(1)

    sys.exit(
        verify_reproducible_builds(
            packages_to_check=packages,
            source_date_epoch=args.epoch,
            format_name=args.format,
        )
    )
