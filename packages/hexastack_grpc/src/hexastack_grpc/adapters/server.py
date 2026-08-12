from collections.abc import Sequence

import grpc
from hexastack_grpc.infra.config import HexastackGrpcConfig


def run_grpc_server(
    server: grpc.Server,
    block: bool = True,
) -> None:
    """Start the gRPC server and optionally block the current thread.

    Args:
        server: Configured grpc.Server instance.
        block: If True, blocks thread with server.wait_for_termination().
    """
    server.start()
    if block:
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            server.stop(grace=5.0)


def create_async_grpc_server(
    config: HexastackGrpcConfig,
    interceptors: Sequence[grpc.aio.ServerInterceptor] | None = None,
) -> grpc.aio.Server:
    """Create an asynchronous grpc.aio.Server instance.

    Args:
        config: HexastackGrpcConfig options.
        interceptors: Optional async server interceptors.

    Returns:
        Configured grpc.aio.Server instance.
    """
    server = grpc.aio.server(interceptors=interceptors or ())
    server.add_insecure_port(f"{config.host}:{config.port}")
    return server


__all__ = [
    "create_async_grpc_server",
    "run_grpc_server",
]
