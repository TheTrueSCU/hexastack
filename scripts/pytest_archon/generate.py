"""Generate pytest-archon boundary tests for packages in Hexagonal Architecture."""

from pathlib import Path

from scripts._common import (
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
    packages = get_package_directories()
    if not packages:
        raise SystemExit("No packages found.")

    for pkg_path in packages:
        generate_tests_for_package(pkg_path)


if __name__ == "__main__":
    main()
