from collections.abc import Callable, Sequence
from concurrent import futures
from dataclasses import dataclass
from typing import Any

import grpc
from hexastack_grpc.domain.exceptions import ServiceRegistrationError
from hexastack_grpc.infra.config import HexastackGrpcConfig
from rodi import Container


@dataclass(frozen=True)
class GrpcServiceRegistration:
    """Dataclass holding registered gRPC servicer and its protobuf attachment hook."""

    servicer: Any
    add_to_server_fn: Callable[[Any, Any], None]
    service_names: Sequence[str] = ()


class GrpcServiceRegistry:
    """Registry maintaining registered gRPC servicers and compiling the server.

    Notes/Architectural Intent:
        Compiles registered generated protobuf servicers into a unified grpc.Server,
        attaching interceptor pipelines and optional Server Reflection.
    """

    def __init__(self) -> None:
        """Initialize empty gRPC registry."""
        self._services: list[GrpcServiceRegistration] = []

    def register_service(
        self,
        servicer: Any,
        add_to_server_fn: Callable[[Any, Any], None],
        service_names: Sequence[str] = (),
    ) -> None:
        """Register a gRPC servicer and its generated add_to_server hook.

        Args:
            servicer: Servicer instance or class.
            add_to_server_fn: Generated protobuf hook (e.g. add_GreeterServicer_to_server).
            service_names: Optional sequence of full service names for reflection.
        """
        reg = GrpcServiceRegistration(
            servicer=servicer,
            add_to_server_fn=add_to_server_fn,
            service_names=service_names,
        )
        if reg not in self._services:
            self._services.append(reg)

    def build_server(
        self,
        config: HexastackGrpcConfig,
        interceptors: Sequence[grpc.ServerInterceptor] | None = None,
        container: Container | None = None,
    ) -> grpc.Server:
        """Construct and populate a grpc.Server instance with registered servicers.

        Args:
            config: HexastackGrpcConfig options.
            interceptors: Optional sequence of ServerInterceptor instances.
            container: Optional rodi DI Container to resolve servicer class dependencies.

        Returns:
            Configured grpc.Server instance.
        """
        thread_pool = futures.ThreadPoolExecutor(max_workers=config.max_workers)
        server = grpc.server(
            thread_pool=thread_pool,
            interceptors=interceptors or (),
        )

        all_service_names: list[str] = []

        for reg in self._services:
            servicer_val = reg.servicer
            if isinstance(servicer_val, type):
                if container is not None:
                    try:
                        servicer_instance = container.resolve(servicer_val)
                    except Exception:  # noqa: BLE001
                        servicer_instance = servicer_val()
                else:
                    servicer_instance = servicer_val()
            else:
                servicer_instance = servicer_val

            try:
                reg.add_to_server_fn(servicer_instance, server)
                all_service_names.extend(reg.service_names)
            except Exception as e:
                raise ServiceRegistrationError(
                    f"Failed to attach {servicer_instance} to gRPC server: {e}"
                ) from e

        if config.enable_reflection:
            try:
                from grpc_reflection.v1alpha import reflection

                names = tuple(all_service_names) + (reflection.SERVICE_NAME,)
                reflection.enable_server_reflection(names, server)
            except ImportError:
                pass

        server.add_insecure_port(f"{config.host}:{config.port}")
        return server

    def clear(self) -> None:
        """Clear all registered services (for test isolation)."""
        self._services.clear()


__all__ = [
    "GrpcServiceRegistration",
    "GrpcServiceRegistry",
]
