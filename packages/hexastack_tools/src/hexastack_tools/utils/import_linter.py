"""Pure utilities for generating and maintaining [tool.importlinter] contracts in pyproject.toml.

Notes/Architectural Intent:
    Generates layer hierarchy and forbidden contract definitions based on
    hexagonal architecture conventions and detected package directory structures.
"""

from __future__ import annotations

import re
from pathlib import Path

from hexastack_tools.utils.workspace import (
    LAYER_RESTRICTIONS,
    get_present_layers,
)

__all__ = [
    "build_import_linter_toml",
    "update_pyproject_toml",
]


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
        for layer in ["infra", "adapters", "ports", "domain"]
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


def update_pyproject_toml(pkg_path: Path) -> bool:
    """Update [tool.importlinter] in a package's pyproject.toml.

    Args:
        pkg_path: Package directory containing pyproject.toml.

    Returns:
        True if modified or updated, False otherwise.
    """
    pkg_name = pkg_path.name.replace("-", "_")
    pyproject_file = pkg_path / "pyproject.toml"

    if not pyproject_file.is_file():
        return False

    present_layers = get_present_layers(pkg_path)
    if not present_layers:
        return False

    linter_config = build_import_linter_toml(pkg_name, present_layers)
    content = pyproject_file.read_text(encoding="utf-8")

    # Strip existing [tool.importlinter] and [[tool.importlinter.contracts]] sections
    cleaned_content = re.sub(
        r"\[\[?tool\.importlinter(?:\.contracts)?\]\]?[\s\S]*?(?=(\n\[|\Z))",
        "",
        content,
    ).strip()

    updated_content = cleaned_content + "\n\n" + linter_config + "\n"
    pyproject_file.write_text(updated_content.lstrip(), encoding="utf-8")
    return True
