from hexastack_grpc.domain.config import HexastackGrpcConfig


def test_hexastack_grpc_config_defaults():
    cfg = HexastackGrpcConfig()
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 50051
    assert cfg.max_workers == 10
    assert cfg.enable_reflection is True
    assert cfg.auto_start is False
