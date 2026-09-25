"""Hexastack Quality & Governance Adapter.

Bridges the Hexaqual engine into Hexastack applications, providing CQRS
dispatching, MCP server tools, reactive DevTools panels, and distributed event
publishing.

Notes/Architectural Intent:
    Serves as the root package for hexastack-qual. Exports package version
    and core domain models while preserving lazy loading for optional extras.
"""

from __future__ import annotations

__version__ = "0.6.0"

__all__ = [
    "__version__",
]
