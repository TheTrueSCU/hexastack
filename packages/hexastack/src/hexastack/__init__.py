import importlib
import importlib.util
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import hexastack_ai as ai
    import hexastack_auth as auth
    import hexastack_cli as cli
    import hexastack_core as core
    import hexastack_cqrs as cqrs
    import hexastack_db as db
    import hexastack_events as events
    import hexastack_fastapi as fastapi
    import hexastack_graphql as graphql
    import hexastack_grpc as grpc
    import hexastack_logging as logging
    import hexastack_mcp as mcp
    import hexastack_otel as otel

__all__ = [
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

_installed_shorthands: list[str] = []

# Dynamically discover and expose only currently installed packages
for _shorthand in __all__:
    _module_name = f"hexastack_{_shorthand}"
    if importlib.util.find_spec(_module_name) is not None:
        try:
            _mod = importlib.import_module(_module_name)
            globals()[_shorthand] = _mod
            sys.modules[f"hexastack.{_shorthand}"] = _mod
            _installed_shorthands.append(_shorthand)
        except (ImportError, AttributeError):
            pass


def __dir__() -> list[str]:
    """Return only installed package shorthands and module globals."""
    return sorted(set(list(globals().keys()) + _installed_shorthands))


def __getattr__(name: str) -> Any:
    """Provide clear guidance when an uninstalled optional package is accessed."""
    if name in __all__:
        raise AttributeError(
            f"Package 'hexastack-{name}' is not installed. "
            f"Install it via 'pip install hexastack[{name}]' or 'pip install hexastack-{name}'."
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
