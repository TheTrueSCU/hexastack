import typer

from hexastack_cli.infra.config import (
    HexastackCliConfig,
    register_cli_config,
)
from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort
from hexastack_cqrs.infra.pipeline import ExecutionPipeline


class CliBootstrapper(BootstrapperPort):
    """Bootstrap extension configuring Hexastack Typer CLI presentation layer.

    Notes/Architectural Intent:
        Implements BootstrapperPort for hexastack-cli (order=40), registering 'cli'
        configuration in Phase 1, creating the Typer application in Phase 2, and registering
        the single-pass CLI discovery visitor.
    """

    name: str = "cli"
    order: int = 40

    def configure(self, context: BootstrapContext) -> None:
        """Phase 2: Instantiate Typer app, configure presenters, and register discovery visitor.

        Args:
            context: BootstrapContext containing DI container, configuration, and properties.

        Returns:
            None.

        Raises:
            None.
        """
        from hexastack_cli.adapters.app import create_cli_app
        from hexastack_cli.infra.autodiscovery import create_cli_visitor

        cfg = HexastackCliConfig()
        if context.config is not None:
            section = context.config.get_section("cli", HexastackCliConfig)
            if section is not None:
                cfg = section

        pipeline = context.properties.get("pipeline")
        if pipeline is None and ExecutionPipeline in context.container:
            pipeline = context.container.resolve(ExecutionPipeline)

        app = create_cli_app(
            config=cfg,
            container=context.container,
            pipeline=pipeline,
        )

        if cfg.auto_register_commands and pipeline is not None:
            visitor = create_cli_visitor(app=app, pipeline=pipeline)
            context.register_visitor(visitor)

        context.container.add_instance(app, declared_class=typer.Typer)
        context.properties["cli_app"] = app

    def register_config(self, registry: ConfigRegistry) -> None:
        """Phase 1: Register CLI configuration schema under 'cli'.

        Args:
            registry: Target ConfigRegistry instance.

        Returns:
            None.

        Raises:
            None.
        """
        register_cli_config(registry)


__all__ = [
    "CliBootstrapper",
]
