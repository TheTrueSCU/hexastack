"""Shared utility functions and constants for Hexastack scripts.

Notes/Architectural Intent:
    Provides common workspace root discovery, package enumeration, and path
    resolution for all maintenance and verification scripts. Ensures scripts
    run reliably regardless of CWD or invocation source.
"""

from __future__ import annotations

from pathlib import Path

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
