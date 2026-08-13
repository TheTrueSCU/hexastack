from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BootstrapperPort(Protocol):
    """Port interface for modular package bootstrapping extensions.

    Notes/Architectural Intent:
        Defines a 2-phase lifecycle enabling packages (e.g. logging, cqrs, web)
        to register configuration schemas and runtime DI services without direct
        cross-package dependencies.
    """

    name: str
    order: int

    def configure(self, context: Any) -> None:
        """Phase 2: Configure runtime dependencies, services, and pipelines.

        Args:
            context: The BootstrapContext containing container, config, and registry.

        Returns:
            None.

        Raises:
            None.
        """
        ...

    def register_config(self, registry: Any) -> None:
        """Phase 1: Register configuration section schemas with ConfigRegistry.

        Args:
            registry: Target ConfigRegistry instance.

        Returns:
            None.

        Raises:
            None.
        """
        ...


__all__ = [
    "BootstrapperPort",
]
