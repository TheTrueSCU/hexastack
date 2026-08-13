from hexastack_auth.infra.config import (
    HexastackAuthConfig,
    register_auth_config,
)
from hexastack_core.infra.registries.config import ConfigRegistry


def test_auth_config_defaults():
    cfg = HexastackAuthConfig()
    assert cfg.algorithm == "HS256"
    assert cfg.token_expire_minutes == 60
    assert cfg.provider == "jwt"
    assert cfg.hasher == "pbkdf2"
    assert cfg.enabled is True


def test_register_auth_config():
    reg = ConfigRegistry()
    register_auth_config(reg)
    assert "auth" in reg
    schema = reg.get("auth")
    assert schema is HexastackAuthConfig
