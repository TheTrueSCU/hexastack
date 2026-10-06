"""Driving and presentation adapters for the Hexastack framework.

Notes/Architectural Intent:
    Exports core CLI extension points. Optional presentation adapters such as
    hexastack-fastapi are loaded lazily to preserve lean CLI startup without
    requiring optional dependencies.
"""

from __future__ import annotations

from hexastack.adapters.cli import add_serve_command

__all__ = [
    "add_serve_command",
]
