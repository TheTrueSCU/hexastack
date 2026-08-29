"""Import linter commands for contract generation and evaluation."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

from hexastack_tools.utils.workspace import (
    LAYER_RESTRICTIONS,
    HexastackScriptArgumentParser,
    get_package_directories,
    get_package_directory,
    get_packages_directory,
    get_present_layers,
    get_repo_root,
)


def _build_layers_contract(pkg_name: str, active_layers: list[str]) -> list[str]:
    """Generate TOML contract for hexagonal architecture layers hierarchy."""
    if len(active_layers) < 2:
        return []
    formatted_layers = "\n".join(f'    "{layer}",' for layer in active_layers)
    return [
        "[[tool.importlinter.contracts]]",
        'name = "Hexagonal architecture layer hierarchy"',
        'type = "layers"',
        f'containers = ["{pkg_name}"]',
        "layers = [",
        formatted_layers,
        "]",
        "",
    ]


def _build_forbidden_contracts(
    pkg_name: str,
    present_layers: set[str],
    active_layers: list[str],
) -> list[str]:
    """Generate TOML contracts for forbidden inter-layer import restrictions."""
    lines: list[str] = []
    for layer, disallowed in LAYER_RESTRICTIONS.items():
        if layer not in present_layers:
            continue

        active_disallowed = [d for d in disallowed if d in present_layers]
        if layer in {"domain", "ports"} and all(
            d in active_layers for d in active_disallowed
        ):
            continue

        if not active_disallowed:
            continue

        source_module = f"{pkg_name}.{layer}"
        forbidden_modules = "\n".join(
            f'    "{pkg_name}.{d}",' for d in active_disallowed
        )

        lines.extend(
            [
                "[[tool.importlinter.contracts]]",
                f'name = "Forbidden imports for {layer}"',
                'type = "forbidden"',
                f'source_modules = ["{source_module}"]',
                "forbidden_modules = [",
                forbidden_modules,
                "]",
                "",
            ]
        )
    return lines


def build_import_linter_toml(pkg_name: str, present_layers: set[str]) -> str:
    """Build the complete [tool.importlinter] TOML section string for a package."""
    active_layers = [
        layer
        for layer in ["adapters", "infra", "ports", "domain"]
        if layer in present_layers
    ]

    header = [
        "[tool.importlinter]",
        f'root_packages = ["{pkg_name}"]',
        "",
    ]
    layers_contract = _build_layers_contract(pkg_name, active_layers)
    forbidden_contracts = _build_forbidden_contracts(
        pkg_name, present_layers, active_layers
    )

    all_lines = header + layers_contract + forbidden_contracts
    return "\n".join(all_lines).strip()


def update_pyproject_toml(pkg_path: Path) -> None:
    """Update [tool.importlinter] in a package's pyproject.toml."""
    pkg_name = pkg_path.name.replace("-", "_")
    pyproject_file = pkg_path / "pyproject.toml"

    if not pyproject_file.is_file():
        return

    present_layers = get_present_layers(pkg_path)
    if not present_layers:
        return

    linter_config = build_import_linter_toml(pkg_name, present_layers)
    content = pyproject_file.read_text()

    content = re.sub(
        r"\[tool\.importlinter\][\s\S]*?(?=(\n\[|\Z))",
        "",
        content,
    ).strip()

    updated_content = content + "\n\n" + linter_config
    pyproject_file.write_text(updated_content.lstrip())


def generate_main() -> None:
    """CLI entrypoint to generate import-linter contracts."""
    parser = HexastackScriptArgumentParser(
        description="Generate [tool.importlinter] contracts in pyproject.toml."
    )
    args = parser.parse_args()

    root = get_repo_root()
    if args.packages:
        packages = [get_package_directory(p, root) for p in args.packages]
    else:
        packages = get_package_directories(root)

    for pkg_path in packages:
        update_pyproject_toml(pkg_path)


def run_main() -> int:
    """CLI entrypoint to run import-linter per package."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    parser = argparse.ArgumentParser(description="Run import-linter per package.")
    parser.add_argument("files", nargs="*", help="Changed files passed by pre-commit")
    parser.add_argument(
        "--all", action="store_true", help="Run across all packages unconditionally"
    )
    args = parser.parse_args()

    packages_dir = get_packages_directory()
    all_packages = get_package_directories()

    if args.all or not args.files:
        targets = [p for p in all_packages if (p / "pyproject.toml").is_file()]
    else:
        targets = []
        for file_str in args.files:
            try:
                rel = Path(file_str).relative_to(packages_dir)
                pkg_dir = packages_dir / rel.parts[0]
                if (pkg_dir / "pyproject.toml").is_file() and pkg_dir not in targets:
                    targets.append(pkg_dir)
            except ValueError:
                continue

    if not targets:
        return 0

    failed = False
    table = Table(
        title="[bold cyan]Hexagonal Architecture Layer Contracts[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Package", style="bold")
    table.add_column("Status", width=12)
    table.add_column("Details")

    for pkg in sorted(targets):
        res = subprocess.run(
            ["lint-imports", "--config", str(pkg / "pyproject.toml")],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            table.add_row(pkg.name, "[bold green]PASSED[/bold green]", "")
        else:
            failed = True
            err = (res.stdout.strip() + "\n" + res.stderr.strip()).strip()
            table.add_row(pkg.name, "[bold red]FAILED[/bold red]", err)

    console.print(table)
    return 1 if failed else 0


__all__ = [
    "build_import_linter_toml",
    "generate_main",
    "run_main",
    "update_pyproject_toml",
]
