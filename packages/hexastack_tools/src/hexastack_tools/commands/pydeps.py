"""Programmatically generate architecture dependency diagrams using pydeps."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor

from hexastack_tools.utils.pydeps import (
    generate_all_diagrams,
    generate_overview_diagram,
    generate_package_diagram,
)
from hexastack_tools.utils.workspace import (
    HexastackScriptArgumentParser,
    ensure_tool_installed,
    get_package_directories,
    get_package_directory,
    get_repo_root,
)

__all__ = [
    "generate_all_diagrams",
    "generate_main",
    "generate_overview_diagram",
    "generate_package_diagram",
]


def generate_main() -> None:
    """CLI entrypoint for pydeps-generate."""
    ensure_tool_installed("pydeps", cli_command="pydeps", extra_name="diagrams")

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
