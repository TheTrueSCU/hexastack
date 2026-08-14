from dataclasses import dataclass

import grpc

from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort
from hexastack_grpc.infra.autodiscovery import create_grpc_visitor
from hexastack_grpc.infra.config import (
    HexastackGrpcConfig,
    register_grpc_config,
)
from hexastack_grpc.infra.decorators import get_grpc_registry
from hexastack_grpc.infra.interceptors.correlation import (
    CorrelationServerInterceptor,
)
from hexastack_grpc.infra.interceptors.exception import (
    ExceptionServerInterceptor,
)
from hexastack_grpc.infra.interceptors.logging import (
    LoggingServerInterceptor,
    TimingServerInterceptor,
)
from hexastack_grpc.infra.registries.service import GrpcServiceRegistry


@dataclass(frozen=True)
class GrpcBootstrapResult:
    """Dataclass holding initialized gRPC server and configuration."""

    config: HexastackGrpcConfig
    server: grpc.Server
    registry: GrpcServiceRegistry


class GrpcBootstrapper(BootstrapperPort):
    """Bootstrap extension configuring and building the gRPC server.

    Notes/Architectural Intent:
        Implements BootstrapperPort with order=40 (executing after CQRS order=20),
        registering the autodiscovery visitor, compiling the gRPC Server with
        telemetry interceptors (correlation, exception mapping, logging, timing),
        and binding it to the DI container.
    """

    name: str = "grpc"
    order: int = 40

    def configure(self, context: BootstrapContext) -> None:
        """Phase 2: Register visitor, assemble gRPC server with interceptors.

        Args:
            context: BootstrapContext containing DI container, config, and properties.

        Returns:
            None.
        """
        cfg = context.get_config("grpc", HexastackGrpcConfig)

        registry = get_grpc_registry()

        # Register visitor for single-pass reflective scanning (Phase 3)
        visitor = create_grpc_visitor(registry)
        context.register_visitor(visitor)

        # 1. Assemble standard interceptors in order
        interceptors = [
            CorrelationServerInterceptor(),
            ExceptionServerInterceptor(),
            LoggingServerInterceptor(),
            TimingServerInterceptor(),
        ]

        # 2. Build grpc.Server instance
        server = registry.build_server(
            config=cfg,
            interceptors=interceptors,
            container=context.container,
        )

        # 3. Register Server and Registry into DI container
        context.container.add_instance(server, declared_class=grpc.Server)
        context.container.add_instance(registry)

        # 4. Auto-start if configured
        if cfg.auto_start:
            server.start()

        # 5. Store in context properties
        result = GrpcBootstrapResult(
            config=cfg,
            server=server,
            registry=registry,
        )
        context.properties["grpc_result"] = result
        context.properties["grpc_server"] = server

    def register_config(self, registry: ConfigRegistry) -> None:
        """Phase 1: Register gRPC configuration schema under 'grpc'.

        Args:
            registry: Target ConfigRegistry instance.

        Returns:
            None.
        """
        register_grpc_config(registry)


__all__ = [
    "GrpcBootstrapResult",
    "GrpcBootstrapper",
]
