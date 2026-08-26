"""Shared utility functions and constants for Hexastack scripts.

Notes/Architectural Intent:
    Provides common workspace root discovery, package enumeration, and path
    resolution for all maintenance and verification scripts. Ensures scripts
    run reliably regardless of CWD or invocation source.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

HEX_LAYERS: list[str] = [
    "domain",
    "ports",
    "adapters",
    "infra",
    "utils",
    "testing",
]

# Prohibited imports per layer: { layer: [layers it MUST NOT import from] }
LAYER_RESTRICTIONS: dict[str, list[str]] = {
    # Domain is the pure core
    "domain": ["ports", "adapters", "infra", "testing"],
    # Ports define interfaces; independent of concrete implementations
    "ports": ["adapters", "infra", "testing"],
    # Adapters implement ports/domain; decoupled from test helpers
    "adapters": ["testing"],
    # Infra handles framework/plumbing; shouldn't import test-only code
    "infra": ["testing"],
    # Utils are low-level shared helpers; must not depend on higher layers
    "utils": ["domain", "ports", "adapters", "infra", "testing"],
}

PACKAGES_DIR = Path("packages")

VALID_PACKAGES: list[str] = sorted(
    [
        "ai",
        "auth",
        "cli",
        "core",
        "cqrs",
        "db",
        "events",
        "fastapi",
        "flags",
        "graphql",
        "grpc",
        "hexastack",
        "logging",
        "mcp",
        "otel",
    ]
)


def get_package_directories(repo_root: Path | None = None) -> list[Path]:
    """Return all package directory paths inside PACKAGES_DIR.

    Args:
        repo_root: Optional repository root Path. Defaults to auto-discovery.

    Returns:
        Sorted list of Path objects for all subdirectories in packages/.

    Raises:
        RuntimeError: If repository root cannot be determined.

    Notes/Architectural Intent:
        Discovers all active subpackages dynamically to support multi-package
        batch operations.
    """
    packages_dir = get_packages_directory(repo_root)
    if not packages_dir.exists():
        return []
    return sorted(p for p in packages_dir.iterdir() if p.is_dir())


def get_package_directory(package: str, repo_root: Path | None = None) -> Path:
    """Return full directory path for a specific package name.

    Args:
        package: Short package name (e.g. 'core') or full name ('hexastack_core', 'hexastack').
        repo_root: Optional repository root Path. Defaults to auto-discovery.

    Returns:
        Absolute or resolved Path to the target package directory.

    Raises:
        RuntimeError: If repository root cannot be determined.

    Notes/Architectural Intent:
        Handles the umbrella package 'hexastack' (at packages/hexastack) as well
        as prefixed packages (packages/hexastack_<name>).
    """
    clean_name = package.removeprefix("hexastack_").removeprefix("hexastack-")
    packages_dir = get_packages_directory(repo_root)

    if clean_name == "hexastack":
        return packages_dir / "hexastack"
    return packages_dir / f"hexastack_{clean_name}"


def get_packages_directory(repo_root: Path | None = None) -> Path:
    """Return the absolute path for PACKAGES_DIR.

    Args:
        repo_root: Optional repository root Path. Defaults to auto-discovery.

    Returns:
        Path pointing to the 'packages' directory.

    Raises:
        RuntimeError: If repository root cannot be determined.

    Notes/Architectural Intent:
        Centralizes the resolution of the packages workspace directory.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    return repo_root / PACKAGES_DIR


def get_present_layers(pkg_path: Path) -> set[str]:
    """Detect which hexagonal layers exist in src/<package_name>/.

    Args:
        pkg_path: Path to the target package root (e.g. packages/hexastack_core).

    Returns:
        Set of layer names (e.g. {'domain', 'ports', 'adapters', 'infra'}) present.

    Raises:
        None.

    Notes/Architectural Intent:
        Inspects directory structure to dynamically configure import-linter contracts
        and pytest-archon tests without hardcoding layer availability per package.
    """
    src_pkg_dir = pkg_path / "src" / pkg_path.name
    if not src_pkg_dir.is_dir():
        return set()
    return {layer for layer in HEX_LAYERS if (src_pkg_dir / layer).is_dir()}


def get_repo_root(start_path: Path | None = None) -> Path:
    """Locate the root directory of the Hexastack repository.

    Traverses upwards from the given start path (defaulting to this file's directory)
    until a directory containing '.git' or 'pyproject.toml' is found.

    Args:
        start_path: Optional starting Path. Defaults to this file's parent directory.

    Returns:
        Resolved absolute Path to repository root.

    Raises:
        RuntimeError: If repository root cannot be determined.

    Notes/Architectural Intent:
        Guarantees scripts run reliably regardless of current working directory
        or whether executed from root, subdirectories, or nested worktrees.
    """
    current = (start_path or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent

    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() or (candidate / "pyproject.toml").is_file():
            return candidate

    raise RuntimeError(
        f"Could not determine repository root starting from '{current}'."
    )


class HexastackScriptArgumentParser(argparse.ArgumentParser):
    """Standardized CLI argument parser for Hexastack maintenance scripts.

    Notes/Architectural Intent:
        Provides consistent options across all scripts:
        - Optional positional files/paths (e.g. from pre-commit)
        - `--package` / `-p` to target specific packages
        - `--path` to target specific subdirectories/files
        - `--all` / `-a` to target all packages unconditionally
    """

    def __init__(self, description: str, **kwargs: Any) -> None:
        super().__init__(description=description, **kwargs)
        self.add_argument(
            "files",
            nargs="*",
            help="Files or paths to process (defaults to all if none specified).",
        )
        self.add_argument(
            "-p",
            "--package",
            dest="packages",
            action="append",
            choices=VALID_PACKAGES,
            help="Target specific package(s) (e.g. -p auth -p core).",
        )
        self.add_argument(
            "--path",
            dest="custom_paths",
            action="append",
            help="Target custom directory or file path(s).",
        )
        self.add_argument(
            "-a",
            "--all",
            action="store_true",
            help="Run across all packages unconditionally.",
        )


def _find_py_files_in_dir(directory: Path) -> list[Path]:
    """Find all .py files in directory recursively."""
    return (
        [p.resolve() for p in directory.glob("**/*.py")] if directory.is_dir() else []
    )


def _resolve_explicit_paths(paths: list[str], root: Path) -> list[Path]:
    """Resolve explicit files and directories to Python files."""
    resolved: set[Path] = set()
    for raw in paths:
        path = Path(raw) if Path(raw).is_absolute() else (root / raw)
        if path.is_file() and path.suffix == ".py":
            resolved.add(path.resolve())
        elif path.is_dir():
            resolved.update(_find_py_files_in_dir(path))
    return sorted(resolved)


def resolve_target_python_files(
    args: argparse.Namespace,
    repo_root: Path | None = None,
) -> list[Path]:
    """Resolve target Python source files based on standard CLI arguments.

    Args:
        args: Parsed CLI arguments from HexastackScriptArgumentParser.
        repo_root: Optional repository root path.

    Returns:
        Sorted list of matching Path objects for Python source files.
    """
    root = repo_root or get_repo_root()

    # 1. If explicit file arguments or paths were passed
    explicit = (args.files or []) + (args.custom_paths or [])
    if explicit:
        return _resolve_explicit_paths(explicit, root)

    # 2. If specific packages were requested
    if args.packages:
        resolved_pkg: set[Path] = set()
        for pkg_name in args.packages:
            resolved_pkg.update(
                _find_py_files_in_dir(get_package_directory(pkg_name, root) / "src")
            )
        return sorted(resolved_pkg)

    # 3. Default or --all: All package src/ directories
    resolved_all: set[Path] = set()
    for pkg_dir in get_package_directories(root):
        resolved_all.update(_find_py_files_in_dir(pkg_dir / "src"))
    return sorted(resolved_all)


def get_package_dependencies(pkg_dir: Path) -> set[str]:
    """Extract internal hexastack package dependencies from a package's pyproject.toml.

    Args:
        pkg_dir: Path to the package directory (e.g. packages/hexastack_fastapi).

    Returns:
        Set of canonical package names (e.g. {'core', 'cqrs'}) depended on.
    """
    pyproject = pkg_dir / "pyproject.toml"
    if not pyproject.is_file():
        return set()

    import tomllib

    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except Exception:
        return set()

    deps: set[str] = set()
    # Check dependencies in [project.dependencies]
    for req in data.get("project", {}).get("dependencies", []):
        name = req.split(">")[0].split("<")[0].split("=")[0].split("[")[0].strip()
        if name.startswith("hexastack"):
            clean = name.removeprefix("hexastack_").removeprefix("hexastack-")
            deps.add("hexastack" if clean == "hexastack" else clean)

    # Check [tool.uv.sources]
    for name in data.get("tool", {}).get("uv", {}).get("sources", {}):
        if name.startswith("hexastack"):
            clean = name.removeprefix("hexastack_").removeprefix("hexastack-")
            deps.add("hexastack" if clean == "hexastack" else clean)

    return deps


def get_workspace_dependency_graph(
    repo_root: Path | None = None,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Build forward and reverse dependency graphs for all workspace packages.

    Args:
        repo_root: Optional repository root path.

    Returns:
        Tuple of:
        - forward_graph: {pkg: set_of_packages_pkg_depends_on}
        - reverse_graph: {pkg: set_of_packages_that_depend_on_pkg}
    """
    root = repo_root or get_repo_root()
    forward: dict[str, set[str]] = {}
    reverse: dict[str, set[str]] = {}

    for pkg_dir in get_package_directories(root):
        clean_name = pkg_dir.name.removeprefix("hexastack_").removeprefix("hexastack-")
        pkg_key = "hexastack" if clean_name == "hexastack" else clean_name

        deps = get_package_dependencies(pkg_dir)
        forward[pkg_key] = deps
        reverse.setdefault(pkg_key, set())

        for d in deps:
            reverse.setdefault(d, set()).add(pkg_key)

    return forward, reverse


def get_downstream_dependents(
    pkg: str,
    reverse_graph: dict[str, set[str]],
) -> set[str]:
    """Compute the transitive closure of all downstream packages that depend on pkg.

    Args:
        pkg: Canonical package name (e.g. 'core' or 'fastapi').
        reverse_graph: Mapping of pkg -> direct dependents.

    Returns:
        Set of all downstream affected packages (including transitive dependents).
    """
    visited: set[str] = set()
    queue = list(reverse_graph.get(pkg, set()))

    while queue:
        current = queue.pop(0)
        if current not in visited:
            visited.add(current)
            queue.extend(reverse_graph.get(current, set()) - visited)

    return visited


def resolve_affected_packages(
    changed_files: list[str],
    repo_root: Path | None = None,
) -> set[str] | None:
    """Determine the set of affected packages given a list of modified file paths.

    Args:
        changed_files: List of file path strings modified in the changeset.
        repo_root: Optional repository root path.

    Returns:
        - Set of canonical package names affected.
        - None if root-level files (e.g. pyproject.toml, conftest.py) changed,
          indicating ALL packages must be tested.
    """
    root = repo_root or get_repo_root()
    _, reverse_graph = get_workspace_dependency_graph(root)

    if not changed_files:
        return set()

    affected: set[str] = set()

    for file_str in changed_files:
        path = Path(file_str)
        try:
            rel_to_root = path.relative_to(root) if path.is_absolute() else path
        except ValueError:
            rel_to_root = path

        parts = rel_to_root.parts

        # Root-level configuration impacts everything
        if len(parts) == 1:
            filename = parts[0]
            if filename in ("pyproject.toml", "uv.lock", "conftest.py"):
                return None  # All packages affected
            continue

        if parts[0] in (".github", "scripts"):
            return None  # CI or tooling change affects all

        if parts[0] == "packages" and len(parts) > 1:
            raw_pkg = parts[1]
            clean_pkg = (
                "hexastack"
                if raw_pkg == "hexastack"
                else raw_pkg.removeprefix("hexastack_")
            )

            if len(parts) == 2 and parts[1] == "pyproject.toml":
                # Package manifest change affects pkg + all downstream
                affected.add(clean_pkg)
                affected.update(get_downstream_dependents(clean_pkg, reverse_graph))
            elif len(parts) > 2:
                sub_dir = parts[2]
                if sub_dir in ("src", "pyproject.toml"):
                    # Source change affects pkg + all downstream
                    affected.add(clean_pkg)
                    affected.update(get_downstream_dependents(clean_pkg, reverse_graph))
                elif sub_dir in ("tests",):
                    # Test-only change affects ONLY this package (no downstream cascade)
                    affected.add(clean_pkg)

    return affected
