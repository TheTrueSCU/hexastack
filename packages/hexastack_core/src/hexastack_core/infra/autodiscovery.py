import importlib
import inspect
import pkgutil
from collections.abc import Callable, Sequence
from types import ModuleType
from typing import Any

type DiscoveryVisitor = Callable[[Any, ModuleType], None]


def scan_modules(
    packages_or_modules: Sequence[str | ModuleType],
    visitors: Sequence[DiscoveryVisitor],
) -> None:
    """Recursively scan modules and subpackages, invoking visitors for each member.

    Notes/Architectural Intent:
        Performs a single unified traversal of the package hierarchy without unnecessary
        class abstractions, dispatching discovered classes and callables to all registered
        visitors across CQRS, FastAPI, and CLI subsystems.

    Args:
        packages_or_modules: Sequence of package names or module objects to inspect.
        visitors: Sequence of visitor callables receiving (member, module).

    Returns:
        None.

    Raises:
        None.
    """
    if not visitors or not packages_or_modules:
        return

    visited: set[str] = set()
    for item in packages_or_modules:
        mod: ModuleType
        if isinstance(item, str):
            try:
                mod = importlib.import_module(item)
            except ImportError:
                continue
        else:
            mod = item

        _scan_module_recursive(mod, visitors, visited)


def _scan_module_recursive(
    mod: ModuleType,
    visitors: Sequence[DiscoveryVisitor],
    visited: set[str],
) -> None:
    """Internal recursive module scanner with cycle prevention."""
    mod_name = getattr(mod, "__name__", "")
    if mod_name in visited:
        return
    visited.add(mod_name)

    # 1. Inspect classes and functions in the module
    for _, obj in inspect.getmembers(
        mod, lambda m: inspect.isclass(m) or inspect.isfunction(m)
    ):
        for visitor in visitors:
            visitor(obj, mod)

    # 2. If it is a package with __path__, recurse over child submodules
    if hasattr(mod, "__path__"):
        for _, sub_name, _ in pkgutil.iter_modules(mod.__path__):
            full_sub_name = f"{mod_name}.{sub_name}"
            try:
                sub_mod = importlib.import_module(full_sub_name)
                _scan_module_recursive(sub_mod, visitors, visited)
            except ImportError:
                continue


__all__ = [
    "DiscoveryVisitor",
    "scan_modules",
]
