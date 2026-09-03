"""Unified Workspace Dependency, Packaging Extras, and Architecture Auditor."""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.commands.deptry import run_deptry_on_package
from hexastack_tools.commands.extras_parity import (
    audit_extras_parity,
    generate_extras_mermaid_diagram,
)
from hexastack_tools.commands.pydeps import generate_all_diagrams
from hexastack_tools.utils.workspace import get_package_directories, get_repo_root

console = Console()


def audit_workspace_dependencies(
    repo_root: Path,
    *,
    check_deptry: bool = True,
    check_extras: bool = True,
    generate_diagrams: bool = False,
) -> tuple[bool, list[str]]:
    """Execute unified audit across packaging extras, source imports, and diagrams.

    Args:
        repo_root: Root directory of the repository workspace.
        check_deptry: Whether to run deptry import audits on each package.
        check_extras: Whether to run optional extras parity auditing.
        generate_diagrams: Whether to regenerate Pydeps SVGs and Mermaid diagrams.

    Returns:
        Tuple of (is_healthy: bool, list_of_error_messages: list[str]).

    Notes/Architectural Intent:
        Unifies code-level import verification (deptry) and pyproject.toml packaging
        forwarding contracts into a single high-performance pipeline.
    """
    errors: list[str] = []

    # 1. Extras Parity Check
    if check_extras:
        extras_violations = audit_extras_parity(repo_root)
        if extras_violations:
            for v in extras_violations:
                errors.append(
                    f"Extras Parity: {v.subpackage}[{v.extra_name}] not properly forwarded in umbrella package."
                )

    # 2. Deptry Source Code Import Check
    if check_deptry:
        for pkg_dir in get_package_directories(repo_root):
            ok, err = run_deptry_on_package(pkg_dir)
            if not ok:
                errors.append(f"Deptry [{pkg_dir.name}]: {err}")

    # 3. Diagram Generation
    if generate_diagrams:
        try:
            generate_all_diagrams(repo_root)
        except Exception as e:
            errors.append(f"Diagram Generation Error: {e}")

    return len(errors) == 0, errors


def main() -> int:
    """CLI entrypoint for unified deps-audit command."""
    parser = argparse.ArgumentParser(
        description="Unified dependency, optional extras, and architecture auditor for Hexastack."
    )
    parser.add_argument(
        "--diagrams",
        action="store_true",
        help="Regenerate all Pydeps SVG import graphs and Mermaid extras diagrams.",
    )
    parser.add_argument(
        "--deptry-only",
        action="store_true",
        help="Only run deptry source import audits.",
    )
    parser.add_argument(
        "--extras-only",
        action="store_true",
        help="Only run optional extras parity checks.",
    )
    args = parser.parse_args()

    repo_root = get_repo_root()

    check_deptry = not args.extras_only
    check_extras = not args.deptry_only

    console.print(
        Panel(
            "[bold cyan]Hexastack Unified Dependency & Packaging Auditor[/bold cyan]",
            subtitle="[dim]deptry + extras parity + architecture diagrams[/dim]",
            expand=False,
        )
    )

    if args.diagrams:
        console.print("[yellow]Generating Pydeps SVGs and Mermaid Extras Diagram...[/yellow]")
        generate_all_diagrams(repo_root)
        mermaid_diag = generate_extras_mermaid_diagram(repo_root)
        diagram_file = repo_root / "docs" / "assets" / "pydeps" / "hexastack_extras.mmd"
        diagram_file.parent.mkdir(parents=True, exist_ok=True)
        diagram_file.write_text(mermaid_diag, encoding="utf-8")
        console.print(f"[bold green]✓ Diagram written to {diagram_file.relative_to(repo_root)}[/bold green]")

    is_healthy, errors = audit_workspace_dependencies(
        repo_root,
        check_deptry=check_deptry,
        check_extras=check_extras,
        generate_diagrams=False,
    )

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Audit Check", style="bold", width=36)
    table.add_column("Status", width=12)

    if check_extras:
        extras_ok = not any(e.startswith("Extras Parity") for e in errors)
        table.add_row(
            "Packaging Extras Parity (15 packages)",
            "[green]✅ Passed[/green]" if extras_ok else "[red]❌ Failed[/red]",
        )

    if check_deptry:
        deptry_ok = not any(e.startswith("Deptry") for e in errors)
        table.add_row(
            "Deptry Source Import Audits",
            "[green]✅ Passed[/green]" if deptry_ok else "[red]❌ Failed[/red]",
        )

    console.print(table)

    if is_healthy:
        console.print(
            "\n[bold green]🎉 All dependencies, optional extras, and packaging contracts are 100% healthy![/bold green]"
        )
        return 0

    console.print("\n[bold red]❌ Found dependency issues:[/bold red]")
    for err in errors:
        console.print(f"  • {err}")
    return 1


__all__ = [
    "audit_workspace_dependencies",
    "main",
]
