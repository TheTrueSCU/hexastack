from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry
from pydantic import BaseModel, Field


@config_section("grpc")
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


def register_grpc_config(registry: ConfigRegistry) -> None:
    """Register gRPC configuration schema under 'grpc'.

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("grpc", HexastackGrpcConfig)


__all__ = [
    "HexastackGrpcConfig",
    "register_grpc_config",
]
