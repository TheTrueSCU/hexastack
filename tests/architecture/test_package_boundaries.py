"""Architecture tests enforcing boundaries across Hexastack packages."""

import ast
import tomllib
from pathlib import Path

import pytest
from pytest_archon import archrule

PACKAGES_ROOT = Path("packages")

ALL_KNOWN_PACKAGES = {
    "hexastack",
    "hexastack_ai",
    "hexastack_auth",
    "hexastack_cli",
    "hexastack_core",
    "hexastack_cqrs",
    "hexastack_db",
    "hexastack_events",
    "hexastack_fastapi",
    "hexastack_graphql",
    "hexastack_grpc",
    "hexastack_logging",
    "hexastack_mcp",
    "hexastack_otel",
}


def get_available_packages() -> set[str]:
    """Return package names currently installed/present under packages/."""
    if not PACKAGES_ROOT.is_dir():
        return set()
    return {
        d.name
        for d in PACKAGES_ROOT.iterdir()
        if d.is_dir() and d.name in ALL_KNOWN_PACKAGES
    }


def _extract_known_packages(raw_deps: list[str]) -> set[str]:
    """Filter list of raw requirement strings for known internal hexastack packages."""
    matched = set()
    for dep in raw_deps:
        for known in ALL_KNOWN_PACKAGES:
            if (
                dep == known
                or dep.startswith(f"{known}[")
                or dep.startswith(f"{known}>=")
            ):
                matched.add(known)
    return matched


def get_declared_dependencies(package_name: str) -> set[str]:
    """Parse dependencies (main + optional) from package pyproject.toml."""
    pyproject_path = PACKAGES_ROOT / package_name / "pyproject.toml"
    if not pyproject_path.is_file():
        return set()

    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    project_data = data.get("project", {})
    deps = _extract_known_packages(project_data.get("dependencies", []))

    optional_deps = project_data.get("optional-dependencies", {})
    for _, extra_list in optional_deps.items():
        deps.update(_extract_known_packages(extra_list))

    return deps


# ----------------------------------------------------------------------
# 1. Hexastack Core Pure Invariant
# ----------------------------------------------------------------------
def test_hexastack_core_imports_no_other_packages():
    """hexastack_core is the absolute base and must not import any other package."""
    available = get_available_packages()
    if "hexastack_core" not in available:
        pytest.skip("hexastack_core is not present.")

    forbidden = [pkg for pkg in available if pkg != "hexastack_core"]
    if not forbidden:
        return

    (
        archrule("Core package must not import any other hexastack packages")
        .match("hexastack_core")
        .should_not_import(*forbidden)
        .check("hexastack_core")
    )


# ----------------------------------------------------------------------
# 2. Inter-Package Boundaries (Configured dynamically via pyproject.toml)
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "package_name", sorted(ALL_KNOWN_PACKAGES - {"hexastack", "hexastack_core"})
)
def test_inter_package_boundaries(package_name: str):
    """Enforce that packages only import core, cqrs, or explicit pyproject.toml deps."""
    available = get_available_packages()
    if package_name not in available:
        pytest.skip(f"{package_name} is not present.")

    # Base allowed packages
    allowed = {"hexastack_core", "hexastack_cqrs", package_name}

    # Add dependencies declared in pyproject.toml (e.g. hexastack_fastapi)
    allowed.update(get_declared_dependencies(package_name))

    forbidden = [pkg for pkg in available if pkg not in allowed]
    if not forbidden:
        return

    (
        archrule(f"{package_name} must only import allowed packages")
        .match(package_name)
        .should_not_import(*forbidden)
        .check(package_name)
    )


# ----------------------------------------------------------------------
# 3. Umbrella Package (hexastack) Re-exports
# ----------------------------------------------------------------------
def test_hexastack_umbrella_imports_all_present_packages():
    """Verify hexastack/__init__.py imports all subpackages present in packages/."""
    available = get_available_packages()
    if "hexastack" not in available:
        pytest.skip("hexastack umbrella package is not present.")

    init_file = PACKAGES_ROOT / "hexastack" / "src" / "hexastack" / "__init__.py"
    if not init_file.is_file():
        pytest.fail(f"Umbrella package entrypoint not found at: {init_file}")

    tree = ast.parse(init_file.read_text())

    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    # All present packages except 'hexastack' itself must be imported/re-exported
    expected_to_import = {pkg for pkg in available if pkg != "hexastack"}
    missing_imports = {
        pkg
        for pkg in expected_to_import
        if not any(
            imported == pkg or imported.startswith(f"{pkg}.")
            for imported in imported_modules
        )
    }

    assert not missing_imports, (
        f"hexastack/__init__.py is missing imports for present packages: {missing_imports}"
    )
