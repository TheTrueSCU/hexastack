import argparse
import subprocess
import sys
from pathlib import Path

from scripts._common import get_package_directories, get_packages_directory

PACKAGES_DIR = get_packages_directory()


def find_packages_to_lint(changed_files: list[str]) -> list[Path]:
    """Identify which package directories need linting based on modified files."""
    all_packages = get_package_directories()

    if not changed_files:
        # If no filenames passed (e.g. manual run or pass_filenames: false), check all
        return [p for p in all_packages if (p / "pyproject.toml").is_file()]

    affected_packages = set()
    for file_path_str in changed_files:
        path = Path(file_path_str)
        try:
            # Check if file resides under packages/<package_name>/
            rel = path.relative_to(PACKAGES_DIR)
            pkg_name = rel.parts[0]
            pkg_dir = PACKAGES_DIR / pkg_name
            if (pkg_dir / "pyproject.toml").is_file():
                affected_packages.add(pkg_dir)
        except ValueError:
            # File outside packages/ directory
            continue

    return sorted(affected_packages)


def run_linter_for_package(pkg_path: Path) -> tuple[bool, str]:
    """Execute lint-imports using the package's pyproject.toml configuration."""
    config_file = pkg_path / "pyproject.toml"
    result = subprocess.run(
        ["lint-imports", "--config", str(config_file)],
        capture_output=True,
        text=True,
    )
    output = (result.stdout.strip() + "\n" + result.stderr.strip()).strip()
    return result.returncode == 0, output


def main() -> int:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    parser = argparse.ArgumentParser(description="Run import-linter per package.")
    parser.add_argument("files", nargs="*", help="Changed files passed by pre-commit")
    parser.add_argument(
        "--all", action="store_true", help="Run across all packages unconditionally"
    )
    args = parser.parse_args()

    if args.all:
        packages = [
            p for p in get_package_directories() if (p / "pyproject.toml").is_file()
        ]
    else:
        packages = find_packages_to_lint(args.files)

    if not packages:
        console.print(
            Panel.fit(
                "[dim]✨ [import-linter] No package changes detected. 0 checks needed.[/dim]",
                border_style="dim",
            )
        )
        return 0

    table = Table(
        title="[bold cyan]Hexagonal Layer & Package Boundary Auditor[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Package", style="bold white", width=25)
    table.add_column("Boundary Contracts", width=35)

    failed = False
    errors = []

    for pkg in packages:
        success, out = run_linter_for_package(pkg)
        if success:
            table.add_row(
                pkg.name, "[bold green]KEPT (All rules satisfied)[/bold green]"
            )
        else:
            table.add_row(pkg.name, "[bold red]BROKEN (Contract violated)[/bold red]")
            errors.append((pkg.name, out))
            failed = True

    console.print()
    console.print(table)
    console.print()

    if failed:
        for pkg_name, out in errors:
            console.print(
                f"[bold red]❌ Boundary Violations in {pkg_name}:[/bold red]\n{out}\n"
            )
        return 1

    console.print(
        Panel.fit(
            f"[bold green]✅ All {len(packages)} inspected package(s) adhere strictly to Hexagonal & layer boundaries![/bold green]",
            border_style="green",
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
