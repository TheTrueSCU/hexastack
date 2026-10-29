"""Infrastructure bootstrapping and DI configuration for UI adapters.

Notes/Architectural Intent:
    Provides automatic registration of UI presentation adapters into ContainerPort.
"""

from __future__ import annotations

from typing import Any

from hexastack_core.ports.container import ContainerPort

__all__ = [
    "UIBootstrapper",
]


class UIBootstrapper:
    """Bootstrapper for Hexastack UI presentation components."""

    @classmethod
    def bootstrap(cls, container: ContainerPort, **kwargs: Any) -> None:
        """Register UI adapters and ports into the DI container.

        Args:
            container: Application ContainerPort instance.
            **kwargs: Extra bootstrap arguments.

        Returns:
            None.

        Notes/Architectural Intent:
            Ensures UI presenters and state providers can be resolved cleanly across services.
        """
        # Future presenter registrations can be bound here
