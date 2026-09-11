"""Programmatic architecture dependency diagram generation utilities using pydeps.

Notes/Architectural Intent:
    Pure generation logic extracted to utils to decouple CLI presentation
    from internal dependency auditor adapters and runner pipelines.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from pydeps.pydeps import pydeps

from hexastack_tools.utils.workspace import (
    ensure_tool_installed,
    get_package_directories,
    get_packages_directory,
)

__all__ = [
    "generate_all_diagrams",
    "generate_overview_diagram",
    "generate_package_diagram",
]

_PYDEPS_ASSET_DIR = Path("docs") / "assets" / "pydeps"


def _output_dir(root: Path) -> Path:
    """Return the absolute path to the pydeps asset directory.

    Args:
        root: Workspace repository root path.

    Returns:
        Absolute Path to pydeps output directory.
    """
    out = root / _PYDEPS_ASSET_DIR
    out.mkdir(parents=True, exist_ok=True)
    return out


def generate_package_diagram(pkg_path: Path, root: Path) -> str | None:
    """Generate a dependency SVG for a single package.

    Args:
        pkg_path: Path to package directory.
        root: Repository root path.

    Returns:
        Relative path string of generated SVG, or None if skipped/errored.
    """
    pkg_name = pkg_path.name
    svg_filename = f"{pkg_name}.svg"
    svg_path = _output_dir(root) / svg_filename
    entry_point = pkg_path / "src" / pkg_name

    if not entry_point.is_dir():
        return None

    try:
        pydeps(
            fname=str(entry_point),
            format="svg",
            output=str(svg_path),
            show=False,
            no_show=True,
            cluster=True,
            max_bacon=2,
            rankdir="TB",
            include_missing=False,
        )
        return str(svg_path.relative_to(root))
    except Exception:
        return None


def generate_overview_diagram(root: Path) -> str | None:
    """Generate the monorepo-wide overview diagram.

    Args:
        root: Repository root path.

    Returns:
        Relative path string of generated SVG, or None if skipped/errored.
    """
    svg_path = _output_dir(root) / "hexastack_packages.svg"
    packages_dir = get_packages_directory(root)

    try:
        pydeps(
            fname=str(packages_dir),
            format="svg",
            output=str(svg_path),
            show=False,
            no_show=True,
            cluster=True,
            max_bacon=1,
            rankdir="TB",
            include_missing=False,
        )
        return str(svg_path.relative_to(root))
    except Exception:
        return None


def generate_all_diagrams(root: Path) -> list[tuple[str, str]]:
    """Programmatically generate overview and all package SVGs.

    Args:
        root: Repository root path.

    Returns:
        List of tuples (package_or_overview_name, relative_svg_path).
    """
    ensure_tool_installed("pydeps", cli_command="pydeps", extra_name="diagrams")
    packages = get_package_directories(root)
    results: list[tuple[str, str]] = []

    overview_path = generate_overview_diagram(root)
    if overview_path:
        results.append(("Monorepo Overview", overview_path))

    with ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(generate_package_diagram, pkg, root): pkg.name
            for pkg in packages
        }
        for future in futures:
            pkg_name = futures[future]
            path = future.result()
            if path:
                results.append((pkg_name, path))

    return results
