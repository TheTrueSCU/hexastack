"""Generate [tool.importlinter] contracts in each package's pyproject.toml."""

import re
from pathlib import Path

from scripts._common import (
    LAYER_RESTRICTIONS,
    get_package_directories,
    get_present_layers,
)


def build_import_linter_toml(pkg_name: str, present_layers: set[str]) -> str:
    """Generate the TOML block for import-linter contracts based on existing layers."""
    lines = [
        "[tool.importlinter]",
        f'root_packages = ["{pkg_name}"]',
        "",
    ]

    # 1. Main Hexagonal Layers Contract (if at least 2 relevant ordered layers exist)
    layer_order = ["adapters", "ports", "domain"]
    active_layers = [layer for layer in layer_order if layer in present_layers]

    if len(active_layers) >= 2:
        formatted_layers = "\n".join(f'    "{layer}",' for layer in active_layers)
        lines.extend(
            [
                "[[tool.importlinter.contracts]]",
                'name = "Hexagonal architecture layer hierarchy"',
                'type = "layers"',
                f'containers = ["{pkg_name}"]',
                "layers = [",
                formatted_layers,
                "]",
                "",
            ]
        )

    # 2. Layer restrictions for infra, utils, domain, etc.
    for layer, disallowed in LAYER_RESTRICTIONS.items():
        if layer not in present_layers:
            continue

        active_disallowed = [d for d in disallowed if d in present_layers]
        # Avoid duplicate layer rules covered by the 'layers' contract above
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

    return "\n".join(lines).strip() + "\n"


def update_pyproject_toml(pkg_path: Path) -> None:
    pkg_name = pkg_path.name
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
    packages = get_package_directories()
    if not packages:
        raise SystemExit("No packages found.")

    for pkg_path in packages:
        update_pyproject_toml(pkg_path)


if __name__ == "__main__":
    main()
