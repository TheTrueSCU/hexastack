"""Generate [tool.importlinter] contracts in each package's pyproject.toml."""

import re
from pathlib import Path

from scripts._common import (
    LAYER_RESTRICTIONS,
    HexastackScriptArgumentParser,
    get_package_directories,
    get_package_directory,
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
        # Avoid duplicate layer rules covered by the 'layers' contract
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
        print(f"Skipping {pkg_name}: 'pyproject.toml' not found.")
        return

    present_layers = get_present_layers(pkg_path)
    if not present_layers:
        print(f"Skipping {pkg_name}: No hexagonal layers found in src/{pkg_name}.")
        return

    linter_config = build_import_linter_toml(pkg_name, present_layers)
    content = pyproject_file.read_text()

    # Remove existing [tool.importlinter] block if present
    content = re.sub(
        r"\[tool\.importlinter\][\s\S]*?(?=(\n\[|\Z))",
        "",
        content,
    ).strip()

    # Append fresh configuration
    updated_content = content + "\n\n" + linter_config
    pyproject_file.write_text(updated_content.lstrip())
    print(f"Updated [tool.importlinter] in {pyproject_file}")


def main() -> None:
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

    if not packages:
        raise SystemExit("No packages found.")

    for pkg_path in packages:
        update_pyproject_toml(pkg_path)


if __name__ == "__main__":
    main()
