"""Shared utility functions and constants for Hexastack scripts.

Notes/Architectural Intent:
    Provides common workspace root discovery, package enumeration, and path
    resolution for all maintenance and verification scripts.
"""

from __future__ import annotations

from pathlib import Path

HEX_LAYERS = ["domain", "ports", "adapters", "infra", "utils", "testing"]

# Prohibited imports per layer: { layer: [layers it MUST NOT import from] }
LAYER_RESTRICTIONS = {
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
        "graphql",
        "grpc",
        "logging",
        "mcp",
        "otel",
    ]
)


def get_package_directories(repo_root: Path | None = None) -> list[Path]:
    """Return all package directory paths inside PACKAGES_DIR."""
    packages_dir = get_packages_directory(repo_root)
    if not packages_dir.exists():
        return []
    return sorted(p for p in packages_dir.iterdir() if p.is_dir())


def get_package_directory(package: str, repo_root: Path | None = None) -> Path:
    """Return full path for a package."""
    return get_packages_directory(repo_root) / f"hexastack_{package}"


def get_packages_directory(repo_root: Path | None = None) -> Path:
    """Return full path for PACKAGES_DIR."""
    if repo_root is None:
        repo_root = get_repo_root()

    return repo_root / PACKAGES_DIR


def get_present_layers(pkg_path: Path) -> set[str]:
    """Detect which hexagonal layers exist in src/<package_name>/."""
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
