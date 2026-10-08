"""Hexastack: A modern Python enterprise hexagonal architecture framework.

Notes/Architectural Intent:
    Root umbrella package aggregating subpackage namespaces. Discovers
    and exposes installed subpackages dynamically while providing helpful
    installation guidance on uninstalled optional extras.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hexastack.subpackages import (
    discover_and_register_subpackages,
    get_subpackage_dir,
    handle_missing_subpackage,
)

if TYPE_CHECKING:
    import hexastack_qual as qual

    import hexastack_ai as ai
    import hexastack_auth as auth
    import hexastack_cli as cli
    import hexastack_core as core
    import hexastack_cqrs as cqrs
    import hexastack_db as db
    import hexastack_events as events
    import hexastack_fastapi as fastapi
    import hexastack_flags as flags
    import hexastack_flow as flow
    import hexastack_graphql as graphql
    import hexastack_grpc as grpc
    import hexastack_logging as logging
    import hexastack_mcp as mcp
    import hexastack_otel as otel
    import hexastack_ui as ui

__all__ = [
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
    "qual",
    "ui",
]

_installed_shorthands = discover_and_register_subpackages(globals(), __all__)


def __dir__() -> list[str]:
    """Return only installed package shorthands and module globals."""
    return get_subpackage_dir(globals(), _installed_shorthands)


def __getattr__(name: str) -> Any:
    """Provide clear guidance when an uninstalled optional package is accessed."""
    return handle_missing_subpackage(name, __all__)
