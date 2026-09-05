"""Shared workspace utility functions and constants for Hexastack Tools.

Notes/Architectural Intent:
    Provides dynamic workspace root discovery, package enumeration, and path
    resolution for all maintenance and verification tools across both monorepos
    (uv workspace / packages/*) and standalone single-package Hexastack projects.
    Ensures tools run reliably regardless of CWD or project layout.
"""

from __future__ import annotations

import argparse
import tomllib
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


def get_repo_root(start_path: Path | None = None) -> Path:
    """Locate the root directory of the workspace or project."""
    current = (start_path or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    candidates = [current, *current.parents]

    # 1. First search for .git directory or a workspace pyproject.toml
    for candidate in candidates:
        if (candidate / ".git").is_dir():
            return candidate
        pyproj = candidate / "pyproject.toml"
        if pyproj.is_file():
            try:
                text = pyproj.read_text(encoding="utf-8")
                if "[tool.uv.workspace]" in text or (candidate / "packages").is_dir():
                    return candidate
            except (OSError, UnicodeDecodeError):
                # Unreadable or invalid pyproject.toml; proceed searching parent dirs
                pass

    # 2. Fallback to any pyproject.toml
    for candidate in candidates:
        if (candidate / "pyproject.toml").is_file():
            return candidate

    raise RuntimeError(
        f"Could not determine repository root starting from '{current}'."
    )


def get_packages_directory(repo_root: Path | None = None) -> Path:
    """Return the path for PACKAGES_DIR if present, or repo root for single-package projects."""
    if repo_root is None:
        repo_root = get_repo_root()

    pkg_dir = repo_root / PACKAGES_DIR
    if pkg_dir.is_dir():
        return pkg_dir
    return repo_root


def _find_workspace_member_dirs(root: Path, root_pyproject: Path) -> list[Path]:
    """Find directories matching tool.uv.workspace members."""
    if not root_pyproject.is_file():
        return []
    try:
        data = tomllib.loads(root_pyproject.read_text(encoding="utf-8"))
        members = data.get("tool", {}).get("uv", {}).get("workspace", {}).get("members")
        if isinstance(members, list):
            found: list[Path] = []
            for pattern in members:
                for p in root.glob(pattern):
                    if p.is_dir() and (p / "pyproject.toml").is_file():
                        found.append(p.resolve())
            return found
    except (OSError, tomllib.TOMLDecodeError):
        # Invalid TOML or unreadable workspace configuration
        pass
    return []


def get_package_directories(repo_root: Path | None = None) -> list[Path]:
    """Return all package directory paths in the workspace dynamically."""
    root = repo_root or get_repo_root()
    root_pyproject = root / "pyproject.toml"

    found = _find_workspace_member_dirs(root, root_pyproject)
    if found:
        return sorted(set(found))

    packages_dir = root / PACKAGES_DIR
    if packages_dir.is_dir():
        pkgs = [
            p.resolve()
            for p in packages_dir.iterdir()
            if p.is_dir() and ((p / "pyproject.toml").is_file() or (p / "src").is_dir())
        ]
        if pkgs:
            return sorted(pkgs)

    if (root / "src").is_dir() and root_pyproject.is_file():
        return [root.resolve()]

    return []


def get_valid_package_names(repo_root: Path | None = None) -> list[str]:
    """Return sorted list of package names discovered in the workspace."""
    root = repo_root or get_repo_root()
    names: set[str] = set()
    for p in get_package_directories(root):
        names.add(p.name)
        for prefix in ("hexastack_", "hexastack-", "hexaqueue_", "hexaqueue-"):
            if p.name.startswith(prefix):
                names.add(p.name[len(prefix) :])
    return sorted(names)


VALID_PACKAGES: list[str] = get_valid_package_names()


def _is_single_package_root_match(root_dir: Path, target: str) -> bool:
    """Check if single-package root directory matches the target name."""
    clean_target = target.replace("-", "_")
    pyproj = root_dir / "pyproject.toml"
    if pyproj.is_file():
        try:
            data = tomllib.loads(pyproj.read_text(encoding="utf-8"))
            p_name = data.get("project", {}).get("name", "")
            if p_name in (target, clean_target, target.replace("_", "-")):
                return True
        except (OSError, tomllib.TOMLDecodeError):
            # Invalid pyproject.toml, fallback to directory heuristics
            pass
    mod_dir = get_package_module_dir(root_dir)
    return bool(mod_dir and mod_dir.name in (target, clean_target))


def get_package_directory(package: str, repo_root: Path | None = None) -> Path:
    """Return full directory path for a specific package name."""
    root = repo_root or get_repo_root()
    pkg_dirs = get_package_directories(root)
    clean_target = package.replace("-", "_")

    for p in pkg_dirs:
        if p == root and _is_single_package_root_match(p, package):
            return p
        if p.name == package or p.name.replace("-", "_") == clean_target:
            return p

    for p in pkg_dirs:
        p_clean = p.name.replace("-", "_")
        if p_clean.endswith(f"_{clean_target}") or p.name.endswith(f"-{package}"):
            return p

    packages_dir = get_packages_directory(root)
    candidate = packages_dir / f"hexastack_{clean_target}"
    return candidate if candidate.exists() else (packages_dir / package)


def get_package_module_dir(pkg_path: Path) -> Path | None:
    """Detect the Python module directory under src/ for a given package path."""
    src_dir = pkg_path / "src"
    if not src_dir.is_dir():
        return None

    # 1. Match src/<pkg_name> or src/<normalized_pkg_name>
    direct = src_dir / pkg_path.name
    if direct.is_dir():
        return direct
    normalized = src_dir / pkg_path.name.replace("-", "_")
    if normalized.is_dir():
        return normalized

    # 2. Pick the first top-level package directory inside src/
    subdirs = [
        p for p in src_dir.iterdir() if p.is_dir() and not p.name.startswith(".")
    ]
    if subdirs:
        return sorted(subdirs)[0]

    return None


def get_present_layers(pkg_path: Path) -> set[str]:
    """Detect which hexagonal layers exist in the package's Python source directory."""
    module_dir = get_package_module_dir(pkg_path)
    if not module_dir or not module_dir.is_dir():
        return set()
    return {layer for layer in HEX_LAYERS if (module_dir / layer).is_dir()}


class HexastackScriptArgumentParser(argparse.ArgumentParser):
    """Standardized CLI argument parser for Hexastack maintenance tools."""

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
    """Resolve target Python source files based on standard CLI arguments."""
    root = repo_root or get_repo_root()

    explicit = (args.files or []) + (args.custom_paths or [])
    if explicit:
        return _resolve_explicit_paths(explicit, root)

    if args.packages:
        resolved_pkg: set[Path] = set()
        for pkg_name in args.packages:
            resolved_pkg.update(
                _find_py_files_in_dir(get_package_directory(pkg_name, root) / "src")
            )
        return sorted(resolved_pkg)

    resolved_all: set[Path] = set()
    for pkg_dir in get_package_directories(root):
        resolved_all.update(_find_py_files_in_dir(pkg_dir / "src"))
    return sorted(resolved_all)


def get_package_dependencies(pkg_dir: Path) -> set[str]:
    """Extract internal workspace package dependencies from a package's pyproject.toml."""
    pyproject = pkg_dir / "pyproject.toml"
    if not pyproject.is_file():
        return set()

    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        # Unreadable or invalid TOML
        return set()

    deps: set[str] = set()
    for req in data.get("project", {}).get("dependencies", []):
        name = req.split(">")[0].split("<")[0].split("=")[0].split("[")[0].strip()
        if name.startswith("hexastack"):
            clean = name.removeprefix("hexastack_").removeprefix("hexastack-")
            deps.add("hexastack" if clean == "hexastack" else clean)

    for name in data.get("tool", {}).get("uv", {}).get("sources", {}):
        if name.startswith("hexastack"):
            clean = name.removeprefix("hexastack_").removeprefix("hexastack-")
            deps.add("hexastack" if clean == "hexastack" else clean)

    return deps


def get_workspace_dependency_graph(
    repo_root: Path | None = None,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Build forward and reverse dependency graphs for all workspace packages."""
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
    """Compute the transitive closure of all downstream packages that depend on pkg."""
    visited: set[str] = set()
    queue = list(reverse_graph.get(pkg, set()))

    while queue:
        current = queue.pop(0)
        if current not in visited:
            visited.add(current)
            queue.extend(reverse_graph.get(current, set()) - visited)

    return visited


def _resolve_file_impact(
    file_str: str,
    root: Path,
    reverse_graph: dict[str, set[str]],
) -> tuple[bool, set[str]]:
    """Determine if a file impacts all packages, or return impacted package set."""
    path = Path(file_str)
    try:
        rel_to_root = path.relative_to(root) if path.is_absolute() else path
    except ValueError:
        rel_to_root = path

    parts = rel_to_root.parts
    if len(parts) == 1:
        if parts[0] in ("pyproject.toml", "uv.lock", "conftest.py"):
            return True, set()
        return False, set()

    if parts[0] in (".github", "examples"):
        return True, set()

    if parts[0] == "packages" and len(parts) > 1:
        raw_pkg = parts[1]
        clean_pkg = (
            "hexastack"
            if raw_pkg == "hexastack"
            else raw_pkg.removeprefix("hexastack_")
        )

        if len(parts) == 2 and parts[1] == "pyproject.toml":
            return False, {
                clean_pkg,
                *get_downstream_dependents(clean_pkg, reverse_graph),
            }
        if len(parts) > 2:
            sub_dir = parts[2]
            if sub_dir in ("src", "pyproject.toml"):
                return False, {
                    clean_pkg,
                    *get_downstream_dependents(clean_pkg, reverse_graph),
                }
            if sub_dir == "tests":
                return False, {clean_pkg}

    return False, set()


def resolve_affected_packages(
    changed_files: list[str],
    repo_root: Path | None = None,
) -> set[str] | None:
    """Determine the set of affected packages given a list of modified file paths."""
    root = repo_root or get_repo_root()
    _, reverse_graph = get_workspace_dependency_graph(root)

    if not changed_files:
        return set()

    affected: set[str] = set()
    for file_str in changed_files:
        impacts_all, pkgs = _resolve_file_impact(file_str, root, reverse_graph)
        if impacts_all:
            return None
        affected.update(pkgs)

    return affected


def check_tool_availability(
    import_name: str,
    cli_command: str | None = None,
) -> tuple[bool, str]:
    """Check if an underlying tool dependency / CLI executable is available in the current environment.

    Args:
        import_name: Python module/package name to import check (e.g. 'importlinter', 'deptry').
        cli_command: Optional CLI binary command name to search in PATH (e.g. 'lint-imports').

    Returns:
        Tuple of (is_available: bool, status_message: str).
    """
    import importlib.util
    import shutil

    if importlib.util.find_spec(import_name) is None:
        cmd_hint = f" (CLI '{cli_command}')" if cli_command else ""
        return False, f"Python package '{import_name}'{cmd_hint} is not installed."

    if cli_command and not shutil.which(cli_command):
        return False, f"CLI executable '{cli_command}' was not found in PATH."

    return True, ""


def ensure_tool_installed(
    import_name: str,
    cli_command: str | None = None,
    extra_name: str | None = None,
) -> None:
    """Validate tool availability and fail with a clear, actionable error message if missing.

    Args:
        import_name: Python package name to verify.
        cli_command: Optional CLI binary command name.
        extra_name: Optional extra group name (e.g. 'mutmut', 'pydeps', 'all').

    Raises:
        SystemExit: If the required tool is not available in the environment.
    """
    import sys

    is_ok, err = check_tool_availability(import_name, cli_command)
    if not is_ok:
        extra_hint = (
            f" or install 'hexastack-tools[{extra_name}]'" if extra_name else ""
        )
        sys.stderr.write(
            f"\n❌ Tool Dependency Missing: {err}\n"
            f"💡 To install: 'uv add --dev {import_name}'{extra_hint}\n\n"
        )
        sys.exit(1)


__all__ = [
    "check_tool_availability",
    "ensure_tool_installed",
    "get_downstream_dependents",
    "get_package_dependencies",
    "get_package_directories",
    "get_package_directory",
    "get_package_module_dir",
    "get_packages_directory",
    "get_present_layers",
    "get_repo_root",
    "get_valid_package_names",
    "get_workspace_dependency_graph",
    "HEX_LAYERS",
    "HexastackScriptArgumentParser",
    "LAYER_RESTRICTIONS",
    "PACKAGES_DIR",
    "resolve_affected_packages",
    "resolve_target_python_files",
    "VALID_PACKAGES",
]
