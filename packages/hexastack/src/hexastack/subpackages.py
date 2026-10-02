"""Subpackage discovery and namespace registration utilities for Hexastack.

Notes/Architectural Intent:
    Encapsulates dynamic subpackage discovery and module namespace binding
    outside of package initializers (`__init__.py`), keeping the umbrella
    package root clean, declarative, and thoroughly testable.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from typing import Any

__all__ = [
    "ALL_SUBPACKAGES",
    "discover_and_register_subpackages",
    "get_subpackage_dir",
    "handle_missing_subpackage",
]

ALL_SUBPACKAGES: list[str] = [
    "ai",
    "auth",
    "cli",
    "core",
    "cqrs",
    "db",
    "events",
    "fastapi",
    "flags",
    "flow",
    "graphql",
    "grpc",
    "logging",
    "mcp",
    "otel",
    "ui",
]


def discover_and_register_subpackages(
    target_globals: dict[str, Any],
    shorthands: list[str],
) -> list[str]:
    """Discover installed subpackages and register them in target namespace.

    Args:
        target_globals: Global namespace dictionary of the caller (e.g. globals()).
        shorthands: List of subpackage shorthand names to probe.

    Returns:
        List of successfully discovered and bound subpackage shorthands.

    Notes/Architectural Intent:
        Iterates through candidate subpackage shorthands, probing each using
        `importlib.util.find_spec`. Successfully imported modules are bound
        both to `target_globals` and `sys.modules[hexastack.<shorthand>]`.
    """
    installed: list[str] = []
    for shorthand in shorthands:
        module_name = f"hexastack_{shorthand}"
        if importlib.util.find_spec(module_name) is not None:
            try:
                mod = importlib.import_module(module_name)
                target_globals[shorthand] = mod
                sys.modules[f"hexastack.{shorthand}"] = mod
                installed.append(shorthand)
            except (ImportError, AttributeError):
                # Optional subpackage import failure; omit from installed list
                pass
    return installed


def get_subpackage_dir(
    target_globals: dict[str, Any],
    installed_shorthands: list[str],
) -> list[str]:
    """Calculate directory listing combining globals and installed shorthands.

    Args:
        target_globals: Global namespace dictionary of the caller.
        installed_shorthands: List of installed subpackage shorthands.

    Returns:
        Sorted list of exposed attribute names.
    """
    return sorted(set(list(target_globals.keys()) + installed_shorthands))


def handle_missing_subpackage(name: str, known_shorthands: list[str]) -> Any:
    """Raise descriptive error when an uninstalled optional package is accessed.

    Args:
        name: Name of the accessed attribute.
        known_shorthands: List of valid ecosystem subpackage shorthands.

    Returns:
        Never returns normally; always raises AttributeError.

    Raises:
        AttributeError: Always raised with installation guidance or missing attribute error.
    """
    if name in known_shorthands:
        raise AttributeError(
            f"Package 'hexastack-{name}' is not installed. "
            f"Install it via 'pip install hexastack[{name}]' or 'pip install hexastack-{name}'."
        )
    raise AttributeError(f"module 'hexastack' has no attribute '{name}'")
