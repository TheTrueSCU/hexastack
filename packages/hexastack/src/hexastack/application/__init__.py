"""Hexastack umbrella application layer.

Sub-packages:
    diagnostics: Interactive architecture diagnostics and registry introspection.
    scaffolding: Developer microservice project scaffolding generator.
"""

from hexastack.application.diagnostics.handlers import (
    GetSystemInfoHandler,
    InspectRegistryHandler,
    PingDemoHandler,
)
from hexastack.application.scaffolding.generator import (
    ProjectScaffolder,
    ScaffoldConfig,
    scaffold_project,
)

__all__ = [
    "GetSystemInfoHandler",
    "InspectRegistryHandler",
    "PingDemoHandler",
    "ProjectScaffolder",
    "scaffold_project",
    "ScaffoldConfig",
]
