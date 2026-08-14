"""Shared utility functions and constants for Hexastack scripts.

Notes/Architectural Intent:
    Provides common workspace root discovery, package enumeration, and path
    resolution for all maintenance and verification scripts.
"""

from __future__ import annotations

from pathlib import Path

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
        if (candidate / ".git").exists() or (
            candidate / "pyproject.toml"
        ).is_file():
            return candidate

    raise RuntimeError(
        f"Could not determine repository root starting from '{current}'."
    )
