from pathlib import Path

from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_grpc.infra.config import (
    HexastackGrpcConfig,
    register_grpc_config,
)


def test_grpc_config_defaults():
    cfg = HexastackGrpcConfig()
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 50051
    assert cfg.max_workers == 10
    assert cfg.enable_reflection is True
    assert cfg.auto_start is False


def test_register_grpc_config(tmp_path: Path):
    reg = ConfigRegistry()
    register_grpc_config(reg)

    cfg_file = tmp_path / "hexastack.toml"
    cfg_file.write_text(
        """
        [hexastack.grpc]
        host = "127.0.0.1"
        port = 50052
        max_workers = 4
        enable_reflection = false
        auto_start = true
        """,
        encoding="utf-8",
    )

    loaded = reg.load_config_toml(cfg_file)
    grpc_cfg = loaded.get_section("grpc", HexastackGrpcConfig)
    assert grpc_cfg is not None
    assert grpc_cfg.host == "127.0.0.1"
    assert grpc_cfg.port == 50052
    assert grpc_cfg.max_workers == 4
    assert grpc_cfg.enable_reflection is False
    assert grpc_cfg.auto_start is True
