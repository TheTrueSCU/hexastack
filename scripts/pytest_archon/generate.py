"""Generate pytest-archon boundary tests for packages in Hexagonal Architecture."""

from pathlib import Path

from scripts._common import (
    HexastackScriptArgumentParser,
    get_package_directories,
    get_package_directory,
    get_present_layers,
    get_repo_root,
)


def generate_tests_for_package(pkg_path: Path) -> None:
    """Generate clean architecture boundary test for a package."""
    pkg_name = pkg_path.name
    present_layers = get_present_layers(pkg_path)

    if not present_layers:
        return

    test_file_lines = [
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

    arch_test_dir = pkg_path / "tests" / "architecture"
    arch_test_dir.mkdir(parents=True, exist_ok=True)
    out_file = arch_test_dir / "test_hexagonal_boundaries.py"

    out_file.write_text("\n".join(test_file_lines).strip() + "\n")
    print(f"Generated clean architecture test in {out_file}")


def main() -> None:
    """CLI entrypoint to generate architecture tests."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    parser = HexastackScriptArgumentParser(
        description="Generate pytest-archon boundary tests for packages."
    )
    args = parser.parse_args()

    root = get_repo_root()
    if args.packages:
        packages = [get_package_directory(p, root) for p in args.packages]
    else:
        packages = get_package_directories(root)

    if not packages:
        raise SystemExit("No packages found.")

    table = Table(
        title="[bold cyan]Architecture Test Generator (pytest-archon)[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Package", style="bold white", width=25)
    table.add_column("Generated Test File", style="cyan", width=55)

    generated = 0
    for pkg_path in packages:
        generate_tests_for_package(pkg_path)
        rel_test = (
            pkg_path.relative_to(root)
            / "tests"
            / "architecture"
            / "test_hexagonal_boundaries.py"
        )
        table.add_row(pkg_path.name, str(rel_test))
        generated += 1

    console.print()
    console.print(table)
    console.print()
    console.print(
        Panel.fit(
            f"[bold green]✨ Generated pytest-archon tests across {generated} package(s).[/bold green]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
