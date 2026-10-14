"""Dynamic module import helpers and optional dependency guards.

Notes/Architectural Intent:
    Provides standardized runtime verification for optional package extras
    without introducing third-party dependencies to hexastack-core.
"""

from __future__ import annotations

import importlib
from typing import Any

from hexastack_core.exceptions import MissingDependencyError


def require_dependency(
    module_name: str,
    *,
    extra: str,
    package: str,
    feature_name: str | None = None,
) -> Any:
    """Import an optional third-party module or raise MissingDependencyError.

    Args:
        module_name: Python module import path (e.g. 'dlt', 'nats', 'filelock').
        extra: Subpackage optional extra name (e.g. 'dlt', 'nats', 'kafka').
        package: PyPI package name (e.g. 'hexastack-events', 'hexastack-core').
        feature_name: Optional human-readable feature/component name for error context.

    Returns:
        The imported module object.

    Raises:
        MissingDependencyError: If the requested module is not installed.

    Notes/Architectural Intent:
        Standardizes optional dependency verification across all hexagonal adapters,
        ensuring actionable error messages directing users to the exact `pip install <package>[<extra>]`
        command required.
    """
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        context = f" for {feature_name}" if feature_name else ""
        raise MissingDependencyError(
            f"Optional dependency '{module_name}' is required{context}. "
            f"Install with: pip install {package}[{extra}]"
        ) from exc


def optional_dependency(
    module_name: str,
    *,
    default: Any = None,
) -> Any:
    """Import an optional third-party module, returning a default value if unavailable.

    Args:
        module_name: Python module import path (e.g. 'hexaflow', 'sentry_sdk').
        default: Fallback value returned if the module is not installed (defaults to None).

    Returns:
        The imported module object, or `default` if ModuleNotFoundError is encountered.

    Notes/Architectural Intent:
        Complements `require_dependency` by providing a safe, clean mechanism for
        progressive feature enhancement in presentation layers, devtools dashboards,
        and diagnostics without boilerplate try/except blocks.
    """
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        return default


__all__ = [
    "optional_dependency",
    "require_dependency",
]
