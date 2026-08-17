#!/usr/bin/env python3
"""Generate pytest-archon boundary tests for packages in Hexagonal Architecture."""

import textwrap
from pathlib import Path

from _common import (
    LAYER_RESTRICTIONS,
    get_package_directories,
    get_present_layers,
)


def generate_tests_for_package(pkg_path: Path) -> None:
    pkg_name = pkg_path.name
    present_layers = get_present_layers(pkg_path)

    if not present_layers:
        return

    test_file_lines = [
        f'"""Hexagonal architecture boundary tests for {pkg_name}."""',
        "",
        "from pytest_archon import archrule",
        "",
    ]

    rule_count = 0
    for layer, disallowed in LAYER_RESTRICTIONS.items():
        if layer not in present_layers:
            continue

        active_disallowed = [d for d in disallowed if d in present_layers]
        if not active_disallowed:
            continue

        rule_count += 1
        source_module = f"{pkg_name}.{layer}"
        target_modules = [f"{pkg_name}.{d}" for d in active_disallowed]
        formatted_targets = ", ".join(f'"{t}"' for t in target_modules)

        rule_def = textwrap.dedent(
            f"""\
            def test_{layer}_boundary_rules():
                (
                    archrule("{layer.capitalize()} layer must not import from forbidden layers")
                    .match("{source_module}")
                    .should_not_import({formatted_targets})
                    .check("{pkg_name}")
                )
            """
        )
        test_file_lines.append(rule_def)

    arch_test_dir = pkg_path / "tests" / "architecture"
    arch_test_dir.mkdir(parents=True, exist_ok=True)
    out_file = arch_test_dir / "test_hexagonal_boundaries.py"

    out_file.write_text("\n".join(test_file_lines).strip() + "\n")
    print(f"Generated {rule_count} rule(s) in {out_file}")


def main() -> None:
    packages = get_package_directories()
    if not packages:
        raise SystemExit("No packages found.")

    for pkg_path in packages:
        generate_tests_for_package(pkg_path)


if __name__ == "__main__":
    main()
