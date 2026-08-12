from fastapi import FastAPI
from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.infra.registries.exception import ExceptionRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort
from hexastack_cqrs.infra.pipeline import ExecutionPipeline

from hexastack_fastapi.infra.config import (
    HexastackFastApiConfig,
    register_fastapi_config,
)


class FastApiBootstrapper(BootstrapperPort):
    """Bootstrap extension configuring FastAPI web presentation layer.

    Notes/Architectural Intent:
        Implements BootstrapperPort for hexastack-fastapi, registering 'fastapi'
        configuration in Phase 1 and creating/binding the FastAPI application instance
        in Phase 2 after logging (order=10) and CQRS pipeline (order=20).
    """

    name: str = "fastapi"
    order: int = 30

    def configure(self, context: BootstrapContext) -> None:
        """Phase 2: Instantiate FastAPI app, configure middleware, and register in container.

        Args:
            context: BootstrapContext containing DI container, configuration, and properties.

        Returns:
            None.

        Raises:
            None.
        """
        from hexastack_fastapi.adapters.app import create_fastapi_app
        from hexastack_fastapi.adapters.routing import CqrsRouter
        from hexastack_fastapi.infra.autodiscovery import create_route_visitor

        cfg = HexastackFastApiConfig()
        if context.config is not None:
            section = context.config.get_section("fastapi", HexastackFastApiConfig)
            if section is not None:
                cfg = section

        pipeline = context.properties.get("pipeline")
        if pipeline is None and ExecutionPipeline in context.container:
            pipeline = context.container.resolve(ExecutionPipeline)

        exception_reg = None
        if ExceptionRegistry in context.container:
            exception_reg = context.container.resolve(ExceptionRegistry)

        app = create_fastapi_app(
            config=cfg,
            container=context.container,
            pipeline=pipeline,
            exception_registry=exception_reg,
        )

        if cfg.auto_register_routes:
            router = CqrsRouter()
            visitor = create_route_visitor(router)
            context.register_visitor(visitor)
            app.include_router(router)

        context.container.add_instance(app, declared_class=FastAPI)
        context.properties["app"] = app

    def register_config(self, registry: ConfigRegistry) -> None:
        """Phase 1: Register FastAPI configuration schema under 'fastapi'.

        Args:
            registry: Target ConfigRegistry instance.

        Returns:
            None.

        Raises:
            None.
        """
        register_fastapi_config(registry)


__all__ = [
    "FastApiBootstrapper",
]
