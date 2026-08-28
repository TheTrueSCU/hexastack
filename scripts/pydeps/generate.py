"""Programmatically generate architecture dependency diagrams using pydeps.

Notes/Architectural Intent:
    Produces SVG diagrams showing both intra-package module structure and
    cross-cutting third-party dependencies, written to ``docs/assets/pydeps/``
    so they are co-located with other documentation assets and embeddable in
    MkDocs pages.

    Two diagram types are generated:

    * **Monorepo overview** (``hexastack_packages.svg``): all packages as
      clusters, third-party libs visible as external nodes.
    * **Per-package diagrams** (``<pkg>.svg``): internal module structure plus
      direct and one-hop-transitive third-party dependencies, clustered and
      collapsed to reduce noise.

    Output directory: ``docs/assets/pydeps/`` (relative to repo root).
    SVGs are committed to version control; CI enforces freshness with
    ``git diff --exit-code docs/assets/pydeps/``.
"""

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from pydeps.pydeps import pydeps

from scripts._common import (
    HexastackScriptArgumentParser,
    get_package_directories,
    get_package_directory,
    get_packages_directory,
    get_repo_root,
)

# Output directory for all generated SVGs
_PYDEPS_ASSET_DIR = Path("docs") / "assets" / "pydeps"


def _output_dir(root: Path) -> Path:
    """Return the absolute path to the pydeps asset directory.

    Args:
        root: Absolute path to the repository root.

    Returns:
        Absolute path to ``docs/assets/pydeps/``, created if absent.

    Notes/Architectural Intent:
        Centralises SVG output to a single well-known location so docs tooling
        (MkDocs, architecture.md) can reference files by stable paths.
    """
    out = root / _PYDEPS_ASSET_DIR
    out.mkdir(parents=True, exist_ok=True)
    return out


def generate_package_diagram(pkg_path: Path, root: Path) -> str | None:
    """Generate a dependency SVG for a single package.

    Shows intra-package modules as a cluster plus visible third-party
    dependencies up to three hops away.  Large third-party libraries are
    collapsed to a single cluster node to avoid visual clutter.

    Args:
        pkg_path: Path to the package root directory (e.g. ``packages/hexastack_core``).
        root: Absolute path to the repository root (used to resolve the output dir).

    Returns:
        The generated SVG filename on success, or None if skipped.

    Notes/Architectural Intent:
        ``only`` is intentionally *not* set so that third-party dependency nodes
        appear in the graph.  ``max_cluster_size=10`` collapses noisy large libs
        (e.g. pydantic, SQLAlchemy) to a single representative node.
        ``rmprefix`` strips the package's own dotted prefix from node labels so
        internal module names are readable without the full qualified path.
    """
    pkg_name = pkg_path.name
    src_dir = pkg_path / "src" / pkg_name
    output_file = _output_dir(root) / f"{pkg_name}.svg"

    if not src_dir.is_dir():
        print(f"Skipping {pkg_name}: '{src_dir}' not found.")
        return None

    print(f"Generating diagram for {pkg_name} -> {output_file.relative_to(root)}...")

    pydeps(
        fname=str(src_dir),
        # Layout
        rankdir="LR",
        # Scope: no `only` filter so third-party nodes are visible
        max_bacon=3,
        max_module_depth=3,
        # Clustering: group external libs, collapse large ones to one node
        cluster=True,
        keep_target_cluster=True,
        min_cluster_size=2,
        max_cluster_size=10,
        # Readability: strip package prefix from internal node labels
        rmprefix=[f"{pkg_name}."],
        # Output
        noshow=True,
        output=str(output_file),
    )
    return f"{pkg_name.replace('-', '_')}.svg"


def generate_monorepo_diagram(root: Path) -> str | None:
    """Generate a high-level cross-package overview diagram.

    Shows all hexastack packages as clusters with shared third-party
    dependencies visible as external nodes, giving a bird's-eye view of
    inter-package and library relationships.

    Args:
        root: Absolute path to the repository root.

    Returns:
        The generated overview SVG filename on success, or None if skipped.

    Notes/Architectural Intent:
        Uses the umbrella ``hexastack`` package as the entry point so pydeps
        can discover all sub-packages via normal import resolution.  ``only``
        is dropped so third-party nodes surface.  ``max_module_depth=2`` keeps
        the overview readable by coalescing deep sub-modules.
    """
    umbrella_src = get_packages_directory() / "hexastack" / "src" / "hexastack"
    output_file = _output_dir(root) / "hexastack_packages.svg"

    if not umbrella_src.is_dir():
        print(f"Skipping monorepo diagram: '{umbrella_src}' not found.")
        return None

    print(f"Generating monorepo overview -> {output_file.relative_to(root)}...")

    pydeps(
        fname=str(umbrella_src),
        # Layout
        rankdir="LR",
        # Scope: broad enough to show cross-package edges plus first-hop externals
        max_bacon=3,
        max_module_depth=2,
        # Clustering
        cluster=True,
        keep_target_cluster=True,
        min_cluster_size=2,
        max_cluster_size=10,
        # Readability: strip top-level hexastack prefix from node labels
        rmprefix=["hexastack."],
        # Output
        noshow=True,
        output=str(output_file),
    )
    return "hexastack_packages.svg"


def main() -> None:
    """CLI entrypoint to generate pydeps architecture diagrams."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    parser = HexastackScriptArgumentParser(
        description="Generate pydeps architecture diagrams in parallel to docs/assets/pydeps/."
    )
    args = parser.parse_args()

    root = get_repo_root()
    generated = []

    # Resolve packages to generate
    if args.packages:
        packages = [get_package_directory(p, root) for p in args.packages]
    else:
        packages = get_package_directories(root)

    table = Table(
        title="[bold cyan]Architecture Dependency Diagram Generator (pydeps)[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Asset / Package", style="bold white", width=30)
    table.add_column("Output File", style="cyan", width=45)

    # Execute diagram generation concurrently across available CPU cores
    tasks = []
    with ProcessPoolExecutor() as executor:
        if not args.packages:
            tasks.append(
                (
                    "Monorepo Overview",
                    "docs/assets/pydeps/hexastack_packages.svg",
                    executor.submit(generate_monorepo_diagram, root),
                )
            )

        for pkg_path in packages:
            svg_name = f"{pkg_path.name.replace('-', '_')}.svg"
            tasks.append(
                (
                    pkg_path.name,
                    f"docs/assets/pydeps/{svg_name}",
                    executor.submit(generate_package_diagram, pkg_path, root),
                )
            )

        for name, out_path, future in tasks:
            result = future.result()
            if result:
                table.add_row(name, out_path)
                generated.append(result)

    console.print()
    console.print(table)
    console.print()
    console.print(
        Panel.fit(
            f"[bold green]✨ Generated {len(generated)} architecture dependency diagram(s) concurrently in docs/assets/pydeps/.[/bold green]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
