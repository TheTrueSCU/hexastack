"""Dynamic module import helpers and optional dependency guards.

Notes/Architectural Intent:
    Provides standardized runtime verification for optional package extras
    without introducing third-party dependencies to hexastack-core.
"""

from __future__ import annotations

import importlib
from typing import Any


def require_dependency(
    module_name: str,
    *,
    extra: str,
    package: str,
    feature_name: str | None = None,
) -> Any:
    """Import an optional third-party module or raise an informative ImportError.

    Args:
        module_name: Python module import path (e.g. 'dlt', 'nats', 'filelock').
        extra: Subpackage optional extra name (e.g. 'dlt', 'nats', 'kafka').
        package: PyPI package name (e.g. 'hexastack-events', 'hexastack-core').
        feature_name: Optional human-readable feature/component name for error context.

    Returns:
        The imported module object.

    Raises:
        ImportError: If the requested module is not installed.

    Notes/Architectural Intent:
        Standardizes optional dependency verification across all hexagonal adapters,
        ensuring actionable error messages directing users to the exact `pip install <package>[<extra>]`
        command required.
    """
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        context = f" for {feature_name}" if feature_name else ""
        raise ImportError(
            f"Optional dependency '{module_name}' is required{context}. "
            f"Install with: pip install {package}[{extra}]"
        ) from exc


__all__ = [
    "require_dependency",
]
