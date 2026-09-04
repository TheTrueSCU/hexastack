from collections.abc import Sequence

import grpc

from hexastack_grpc.domain.config import HexastackGrpcConfig

__all__ = [
    "create_async_grpc_server",
    "run_grpc_server",
]


def create_async_grpc_server(
    config: HexastackGrpcConfig | None = None,
    *,
    host: str | None = None,
    port: int | None = None,
    interceptors: Sequence[grpc.aio.ServerInterceptor] | None = None,
) -> grpc.aio.Server:
    """Create an asynchronous grpc.aio.Server instance.

    Args:
        config: Optional HexastackGrpcConfig instance.
        host: Optional host interface to bind to.
        port: Optional port number to bind to.
        interceptors: Optional async server interceptors.

    Returns:
        Configured grpc.aio.Server instance.
    """
    bind_host = host or (config.host if config else "0.0.0.0")
    bind_port = port if port is not None else (config.port if config else 50051)
    server = grpc.aio.server(interceptors=interceptors or ())
    server.add_insecure_port(f"{bind_host}:{bind_port}")
    return server


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
