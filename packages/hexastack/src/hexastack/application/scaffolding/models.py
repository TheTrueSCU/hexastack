"""Scaffolding data models and configuration types.

Notes/Architectural Intent:
    Encapsulates parameter structures for generating hexagonal microservice projects.
    Separated from generator and templates to eliminate cyclic dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TemplateType = Literal[
    "minimal",
    "web-api",
    "event-driven",
    "mcp-agent",
    "enterprise",
    "grpc-service",
    "graphql-service",
]


@dataclass(frozen=True)
class ScaffoldConfig:
    """Configuration parameters for scaffolding a new Hexastack project."""

    name: str
    template: str = "web-api"

    description: str = "A modern microservice powered by Hexastack."
    python_version: str = ">=3.13"
    db_type: str = "in-memory"  # in-memory, sqlite, postgres
    include_events: bool = False
    include_mcp: bool = False
    include_grpc: bool = False
    include_graphql: bool = False
    include_release: bool = False
    include_openssf: bool = False


__all__ = [
    "ScaffoldConfig",
    "TemplateType",
]
