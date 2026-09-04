from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_grpc.domain.config import HexastackGrpcConfig

config_section("grpc")(HexastackGrpcConfig)

__all__ = [
    "HexastackGrpcConfig",
    "register_grpc_config",
]


def register_grpc_config(registry: ConfigRegistry) -> None:
    """Register gRPC configuration schema under 'grpc'.

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("grpc", HexastackGrpcConfig)
