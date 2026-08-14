from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort
from hexastack_core.ports.logging import LoggingPort

from hexastack_logging.adapters.logger.structured import StructuredLogger
from hexastack_logging.infra.config import (
    HexastackLoggingConfig,
    register_logging_config,
)


class LoggingBootstrapper(BootstrapperPort):
    """Bootstrap extension initializing logging configuration and LoggingPort adapter.

    Notes/Architectural Intent:
        Implements BootstrapperPort for hexastack-logging, registering 'logging'
        config section in Phase 1 and binding StructuredLogger into rodi DI in Phase 2.
    """

    name: str = "logging"
    order: int = 10

    def configure(self, context: BootstrapContext) -> None:
        """Phase 2: Configure root logging and register StructuredLogger in container.

        Args:
            context: BootstrapContext containing DI container and loaded config.

        Returns:
            None.

        Raises:
            None.
        """
        if LoggingPort not in context.container:
            cfg = context.get_config("logging", HexastackLoggingConfig)
            logger = StructuredLogger(config=cfg)
            context.container.add_instance(logger, declared_class=LoggingPort)
            context.properties["logger"] = logger
        else:
            context.properties["logger"] = context.container.resolve(LoggingPort)

    def register_config(self, registry: ConfigRegistry) -> None:
        """Phase 1: Register logging configuration schema under 'logging'.

        Args:
            registry: Target ConfigRegistry instance.

        Returns:
            None.

        Raises:
            None.
        """
        register_logging_config(registry)
