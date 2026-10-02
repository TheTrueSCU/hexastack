"""Infrastructure bootstrap and configuration for hexastack-flow.

Notes/Architectural Intent:
    Provides DI container registration and framework initialization hooks.
"""

from hexastack_flow.infra.bootstrap import FlowBootstrapper

__all__ = [
    "FlowBootstrapper",
]
