import importlib.util
from dataclasses import dataclass
from typing import Any

import strawberry
from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort
from hexastack_graphql.infra.autodiscovery import create_graphql_visitor
from hexastack_graphql.infra.config import (
    HexastackGraphQLConfig,
    register_graphql_config,
)
from hexastack_graphql.infra.decorators import get_schema_registry
from hexastack_graphql.infra.extensions import CorrelationExtension


@dataclass(frozen=True)
class GraphQLBootstrapResult:
    """Dataclass holding compiled GraphQL schema and configuration."""

    config: HexastackGraphQLConfig
    schema: strawberry.Schema
    router: Any | None = None


class GraphQLBootstrapper(BootstrapperPort):
    """Bootstrap extension compiling Strawberry schema and mounting FastAPI router.

    Notes/Architectural Intent:
        Implements BootstrapperPort with order=35 (executing after CQRS order=20
        and FastAPI order=30), registering the autodiscovery visitor, assembling
        the Strawberry Schema with telemetry extensions, and dynamically mounting
        the GraphQL router into the FastAPI application if present.
    """

    name: str = "graphql"
    order: int = 35

    def configure(self, context: BootstrapContext) -> None:
        """Phase 2: Register visitor, compile Strawberry schema, and mount into FastAPI.

        Args:
            context: BootstrapContext containing DI container, config, and properties.

        Returns:
            None.

        Raises:
            None.
        """
        cfg = HexastackGraphQLConfig()
        if context.config is not None:
            section = context.config.get_section("graphql", HexastackGraphQLConfig)
            if section is not None:
                cfg = section

        registry = get_schema_registry()

        # Register visitor for single-pass reflective scanning (Phase 3)
        visitor = create_graphql_visitor(registry)
        context.register_visitor(visitor)

        # 1. Compile schema from registry with CorrelationExtension class
        extensions = [CorrelationExtension]
        schema = registry.build_schema(extensions=extensions)

        # 2. Register Schema and Registry into DI container
        context.container.add_instance(schema, declared_class=strawberry.Schema)
        context.container.add_instance(registry)

        # 3. Mount onto FastAPI app if available and configured
        router = None
        if cfg.auto_mount_fastapi and importlib.util.find_spec("fastapi") is not None:
            fastapi_app = context.properties.get("app")
            if fastapi_app is not None:
                from hexastack_graphql.adapters.fastapi import (
                    create_graphql_router,
                )

                router = create_graphql_router(
                    schema=schema,
                    container=context.container,
                    graphiql=cfg.graphiql,
                )
                fastapi_app.include_router(router, prefix=cfg.path)

        # 4. Store in context properties
        result = GraphQLBootstrapResult(
            config=cfg,
            schema=schema,
            router=router,
        )
        context.properties["graphql_result"] = result
        context.properties["graphql_schema"] = schema
        context.properties["graphql_router"] = router

    def register_config(self, registry: ConfigRegistry) -> None:
        """Phase 1: Register GraphQL configuration schema under 'graphql'.

        Args:
            registry: Target ConfigRegistry instance.

        Returns:
            None.

        Raises:
            None.
        """
        register_graphql_config(registry)


__all__ = [
    "GraphQLBootstrapResult",
    "GraphQLBootstrapper",
]
