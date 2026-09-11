"""PyPI Monorepo Distribution Builder, Checker, and Smart Publisher."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

import httpx
from rich.console import Console
from rich.table import Table

from hexastack_tools.utils.workspace import get_package_directories, get_repo_root

console = Console()


@dataclass(frozen=True)
class PackageMetadata:
    """Metadata for a discovered monorepo subpackage."""

    name: str
    version: str
    dir_path: Path
    pyproject_path: Path


def get_workspace_packages_metadata() -> list[PackageMetadata]:
    """Discover all packages in the workspace and extract their name and version."""
    repo_root = get_repo_root()
    pkg_dirs = get_package_directories(repo_root)
    packages: list[PackageMetadata] = []

    for pkg_dir in pkg_dirs:
        pyproject = pkg_dir / "pyproject.toml"
        if not pyproject.is_file():
            continue

        try:
            content = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            project = content.get("project", {})
            name = project.get("name")
            version = project.get("version")
            if name and version:
                packages.append(
                    PackageMetadata(
                        name=name,
                        version=version,
                        dir_path=pkg_dir,
                        pyproject_path=pyproject,
                    )
                )
        except Exception:
            continue

    return sorted(packages, key=lambda p: p.name)


def check_pypi_version_exists(package_name: str, version: str) -> bool:
    """Check if a specific package version is already released on PyPI."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            if resp.status_code == 404:
                return False
            if resp.status_code == 200:
                data = resp.json()
                releases = data.get("releases", {})
                return version in releases
    except Exception:
        return False
    return False


def build_all_packages(out_dir: Path | None = None) -> int:
    """Build distribution artifacts for all workspace packages."""
    repo_root = get_repo_root()
    target_dist = out_dir or (repo_root / "dist")
    target_dist.mkdir(parents=True, exist_ok=True)

    packages = get_workspace_packages_metadata()
    if not packages:
        return 1

    table = Table(
        title=f"[bold cyan]PyPI Monorepo Distribution Builder -> {target_dist}[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Package Name", style="bold")
    table.add_column("Version", width=12)
    table.add_column("Status", width=16)

    failures: list[str] = []
    for pkg in packages:
        cmd = ["uv", "build", "--package", pkg.name, "--out-dir", str(target_dist)]
        res = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
        if res.returncode == 0:
            table.add_row(pkg.name, pkg.version, "[bold green]✓ Built[/bold green]")
        else:
            failures.append(pkg.name)
            table.add_row(pkg.name, pkg.version, "[bold red]✗ Failed[/bold red]")

    console.print(table)
    return 1 if failures else 0


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
    args = parser.parse_args()
    if args.reproducible_check:
        repro_rc = verify_reproducible_builds()
        if repro_rc != 0:
            sys.exit(repro_rc)
    sys.exit(build_all_packages(out_dir=args.out_dir))


def check_main() -> None:
    """CLI entrypoint for pypi-check."""
    parser = argparse.ArgumentParser(
        description="Verify package release version availability against PyPI index."
    )
    parser.parse_args()

    packages = get_workspace_packages_metadata()
    table = Table(
        title="[bold cyan]PyPI Release Version Availability Checker[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Package Name", style="bold")
    table.add_column("Local Version", width=14)
    table.add_column("PyPI Status", width=24)

    for pkg in packages:
        exists = check_pypi_version_exists(pkg.name, pkg.version)
        status_styled = (
            "[yellow]Already Released[/yellow]"
            if exists
            else "[bold green]Available for Release[/bold green]"
        )
        table.add_row(pkg.name, pkg.version, status_styled)

    console.print(table)


def _find_package_dist_files(target_dist: Path, pkg: PackageMetadata) -> list[Path]:
    """Locate built wheel/sdist distributions for a package in the target dist directory."""
    pkg_underscore = pkg.name.replace("-", "_")
    dist_files = list(target_dist.glob(f"{pkg_underscore}-{pkg.version}*")) + list(
        target_dist.glob(f"{pkg.name}-{pkg.version}*")
    )
    return list({f.resolve(): f for f in dist_files}.values())


def _upload_package(
    pkg: PackageMetadata,
    dist_files: list[Path],
    repo_root: Path,
    auth_token: str | None,
) -> tuple[bool, str]:
    """Execute uv publish for package distribution files and classify outcome.

    Returns:
        tuple[bool, str]: (is_success, status_or_reason)
    """
    cmd = ["uv", "publish"]
    if auth_token:
        cmd.extend(["--token", auth_token])
    cmd.extend([str(f) for f in dist_files])

    console.print(f"📦 Uploading [bold]{pkg.name}[/bold] {pkg.version}...")
    res = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)

    if res.returncode == 0:
        return True, "published"

    err_msg = res.stderr or res.stdout
    err_msg_lower = err_msg.lower()
    if "429" in err_msg or "too many" in err_msg_lower or "rate limit" in err_msg_lower:
        return False, "rate_limited"
    if "already exists" in err_msg_lower or "file already exists" in err_msg_lower:
        return False, "already_exists"
    return False, "failed"


def _process_single_package(
    pkg: PackageMetadata,
    target_dist: Path,
    repo_root: Path,
    auth_token: str | None,
    table: Table,
    delay: float,
    skip_existing: bool,
) -> str:
    """Process a single package release check and upload attempt.

    Returns:
        str: Outcome category ('published', 'skipped', or 'failed').
    """
    if skip_existing and check_pypi_version_exists(pkg.name, pkg.version):
        table.add_row(
            pkg.name,
            pkg.version,
            "[bold yellow]Skipped (Already on PyPI)[/bold yellow]",
        )
        return "skipped"

    dist_files = _find_package_dist_files(target_dist, pkg)
    if not dist_files:
        table.add_row(
            pkg.name,
            pkg.version,
            "[bold red]Failed (No dist files found)[/bold red]",
        )
        return "failed"

    is_success, outcome = _upload_package(pkg, dist_files, repo_root, auth_token)
    if is_success:
        table.add_row(pkg.name, pkg.version, "[bold green]✓ Published[/bold green]")
        if delay > 0:
            time.sleep(delay)
        return "published"
    if outcome == "already_exists":
        table.add_row(
            pkg.name,
            pkg.version,
            "[bold yellow]Skipped (Already Exists)[/bold yellow]",
        )
        return "skipped"
    if outcome == "rate_limited":
        table.add_row(
            pkg.name,
            pkg.version,
            "[bold red]Rate Limited (429 - Cooldown needed)[/bold red]",
        )
        return "failed"

    table.add_row(pkg.name, pkg.version, "[bold red]Upload Failed[/bold red]")
    return "failed"


def publish_packages(
    packages_to_publish: list[PackageMetadata] | None = None,
    dist_dir: Path | None = None,
    token: str | None = None,
    delay: float = 3.0,
    skip_existing: bool = True,
) -> int:
    """Publish built package distributions to PyPI with smart duplicate skipping and rate-limit detection."""
    repo_root = get_repo_root()
    target_dist = dist_dir or (repo_root / "dist")
    auth_token = (
        token or os.environ.get("UV_PUBLISH_TOKEN") or os.environ.get("PYPI_TOKEN")
    )

    all_packages = packages_to_publish or get_workspace_packages_metadata()
    if not all_packages:
        console.print("[bold yellow]No workspace packages discovered.[/bold yellow]")
        return 0

    table = Table(
        title="[bold cyan]PyPI Smart Publisher[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Package Name", style="bold")
    table.add_column("Version", width=12)
    table.add_column("Status", width=36)

    counts = {"published": 0, "skipped": 0, "failed": 0}

    for pkg in all_packages:
        outcome = _process_single_package(
            pkg=pkg,
            target_dist=target_dist,
            repo_root=repo_root,
            auth_token=auth_token,
            table=table,
            delay=delay,
            skip_existing=skip_existing,
        )
        counts[outcome] = counts.get(outcome, 0) + 1

    console.print(table)
    console.print(
        f"\n[bold]Summary:[/bold] {counts['published']} published, {counts['skipped']} skipped, {counts['failed']} failed."
    )
    return 1 if counts["failed"] > 0 else 0


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
    args = parser.parse_args()

    if args.build:
        build_rc = build_all_packages(out_dir=args.dist_dir)
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
        )
    )


def verify_reproducible_builds(
    packages_to_check: list[PackageMetadata] | None = None,
    source_date_epoch: str | None = None,
) -> int:
    """Verify that packages produce byte-for-byte reproducible wheel and sdist distributions.

    Notes/Architectural Intent:
        Satisfies OpenSSF Best Practices Gold requirement [build_reproducible] and SLSA
        Level 3 build determinism standards. Builds artifacts twice into isolated temporary
        locations under identical SOURCE_DATE_EPOCH timestamps and compares SHA-256 digests.

    Args:
        packages_to_check: Optional list of packages to audit. Defaults to all workspace packages.
        source_date_epoch: Optional Unix timestamp epoch string. Defaults to git commit timestamp or 1700000000.

    Returns:
        0 if all distribution artifacts match byte-for-byte, 1 if any mismatch or build failure occurs.
    """
    repo_root = get_repo_root()
    packages = packages_to_check or get_workspace_packages_metadata()
    if not packages:
        return 1

    epoch = source_date_epoch or os.environ.get("SOURCE_DATE_EPOCH")
    if not epoch:
        try:
            res = subprocess.run(
                ["git", "log", "-1", "--pretty=%ct"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            epoch = res.stdout.strip()
        except Exception:
            epoch = "1700000000"

    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = epoch

    table = Table(
        title=f"[bold cyan]PyPI Reproducible Build Auditor (SOURCE_DATE_EPOCH={epoch})[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Package Name", style="bold")
    table.add_column("Artifact File", style="cyan")
    table.add_column("SHA-256 (Run 1 / Run 2)", style="dim")
    table.add_column("Reproducibility", width=18)

    all_matched = True

    with (
        tempfile.TemporaryDirectory(prefix="repro_run1_") as t1,
        tempfile.TemporaryDirectory(prefix="repro_run2_") as t2,
    ):
        p1 = Path(t1)
        p2 = Path(t2)

        for pkg in packages:
            cmd1 = ["uv", "build", "--package", pkg.name, "--out-dir", str(p1)]
            res1 = subprocess.run(
                cmd1, cwd=repo_root, env=env, capture_output=True, text=True
            )
            cmd2 = ["uv", "build", "--package", pkg.name, "--out-dir", str(p2)]
            res2 = subprocess.run(
                cmd2, cwd=repo_root, env=env, capture_output=True, text=True
            )

            if res1.returncode != 0 or res2.returncode != 0:
                all_matched = False
                table.add_row(
                    pkg.name, "*", "Build error", "[bold red]✗ Build Failed[/bold red]"
                )
                continue

            pkg_files_1 = _find_package_dist_files(p1, pkg)
            if not pkg_files_1:
                all_matched = False
                table.add_row(
                    pkg.name,
                    "*",
                    "No files generated",
                    "[bold red]✗ Missing[/bold red]",
                )
                continue

            for f1 in pkg_files_1:
                f2 = p2 / f1.name
                if not f2.is_file():
                    all_matched = False
                    table.add_row(
                        pkg.name,
                        f1.name,
                        "File missing in Run 2",
                        "[bold red]✗ Missing[/bold red]",
                    )
                    continue

                h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
                h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
                if h1 == h2:
                    table.add_row(
                        pkg.name,
                        f1.name,
                        f"{h1[:16]}...",
                        "[bold green]✓ Reproducible[/bold green]",
                    )
                else:
                    all_matched = False
                    table.add_row(
                        pkg.name,
                        f1.name,
                        f"{h1[:8]} != {h2[:8]}",
                        "[bold red]✗ Mismatch[/bold red]",
                    )

    console.print(table)
    if all_matched:
        console.print(
            "[bold green]All package distributions are 100% byte-for-byte reproducible![/bold green]"
        )
        return 0
    console.print(
        "[bold red]One or more package distributions produced non-deterministic outputs.[/bold red]"
    )
    return 1


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
            packages_to_check=packages, source_date_epoch=args.epoch
        )
    )


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
