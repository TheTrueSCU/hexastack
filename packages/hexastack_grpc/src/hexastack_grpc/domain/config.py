from pydantic import BaseModel, Field


class HexastackGrpcConfig(BaseModel):
    """Configuration schema for Hexastack gRPC server adapter.

    Notes/Architectural Intent:
        Configures host binding, port, worker thread pools, and reflection support.
    """

    host: str = Field(
        default="0.0.0.0",
        description="Host interface address to bind the gRPC server to.",
    )
    port: int = Field(
        default=50051,
        description="Port number to listen for incoming gRPC connections.",
    )
    max_workers: int = Field(
        default=10,
        description="Maximum worker threads allocated in the gRPC thread pool executor.",
    )
    enable_reflection: bool = Field(
        default=True,
        description="Enable gRPC Server Reflection protocol for grpcurl and postman discovery.",
    )
    auto_start: bool = Field(
        default=False,
        description="Automatically start the gRPC server in a background thread on bootstrap.",
    )


__all__ = [
    "HexastackGrpcConfig",
]
