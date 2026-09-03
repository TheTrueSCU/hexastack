"""Programmatically generate architecture dependency diagrams using pydeps."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from pydeps.pydeps import pydeps

from hexastack_tools.utils.workspace import (
    HexastackScriptArgumentParser,
    get_package_directories,
    get_package_directory,
    get_packages_directory,
    get_repo_root,
)

_PYDEPS_ASSET_DIR = Path("docs") / "assets" / "pydeps"


def _output_dir(root: Path) -> Path:
    """Return the absolute path to the pydeps asset directory."""
    out = root / _PYDEPS_ASSET_DIR
    out.mkdir(parents=True, exist_ok=True)
    return out


def generate_package_diagram(pkg_path: Path, root: Path) -> str | None:
    """Generate a dependency SVG for a single package."""
    pkg_name = pkg_path.name
    svg_filename = f"{pkg_name}.svg"
    svg_path = _output_dir(root) / svg_filename
    entry_point = pkg_path / "src" / pkg_name

    if not entry_point.is_dir():
        return None

    try:
        pydeps(
            fname=str(entry_point),
            T="svg",
            o=str(svg_path),
            noshow=True,
            cluster=True,
            max_bacon=2,
            rankdir="TB",
            include_missing=False,
            display=None,
        )
        return str(svg_path.relative_to(root))
    except Exception:
        return None


def generate_overview_diagram(root: Path) -> str | None:
    """Generate the monorepo-wide overview diagram."""
    svg_path = _output_dir(root) / "hexastack_packages.svg"
    packages_dir = get_packages_directory(root)

    try:
        pydeps(
            fname=str(packages_dir),
            T="svg",
            o=str(svg_path),
            noshow=True,
            cluster=True,
            max_bacon=1,
            rankdir="TB",
            include_missing=False,
            display=None,
        )
        return str(svg_path.relative_to(root))
    except Exception:
        return None


def generate_main() -> None:
    """CLI entrypoint for pydeps-generate."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    parser = HexastackScriptArgumentParser(
        description="Generate architecture dependency diagrams using pydeps."
    )
    args = parser.parse_args()

    root = get_repo_root()
    if args.packages:
        packages = [get_package_directory(p, root) for p in args.packages]
    else:
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

    table = Table(
        title="[bold cyan]Architecture Dependency Diagram Generator (pydeps)[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Asset / Package", style="bold")
    table.add_column("Output File", style="blue")

    for name, out in results:
        table.add_row(name, out)

    console.print(table)
    console.print(
        Panel.fit(
            f"[bold green]✨ Generated {len(results)} architecture dependency diagram(s) concurrently in docs/assets/pydeps/.[/bold green]",
            border_style="green",
        )
    )


def generate_all_diagrams(root: Path) -> list[tuple[str, str]]:
    """Programmatically generate overview and all package SVGs."""
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


__all__ = [
    "generate_all_diagrams",
    "generate_main",
    "generate_overview_diagram",
    "generate_package_diagram",
]

