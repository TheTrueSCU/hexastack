from hexastack_auth.infra.config import (
    HexastackAuthConfig,
    register_auth_config,
)
from hexastack_core.infra.registries.config import ConfigRegistry


def test_auth_config_defaults():
    cfg = HexastackAuthConfig()
    assert cfg.secret_key == "hexastack-dev-secret-key-change-in-production"
    assert cfg.algorithm == "HS256"
    assert cfg.token_expire_minutes == 60
    assert cfg.issuer is None
    assert cfg.audience is None
    assert cfg.provider == "jwt"
    assert cfg.hasher == "pbkdf2"
    assert cfg.enabled is True


def test_auth_config_custom_values():
    cfg = HexastackAuthConfig(
        secret_key="custom-prod-secret-key",
        algorithm="HS512",
        token_expire_minutes=120,
        issuer="https://auth.hexastack.io",
        audience="hexastack-backend",
        provider="memory",
        hasher="memory",
        enabled=False,
    )
    assert cfg.secret_key == "custom-prod-secret-key"
    assert cfg.algorithm == "HS512"
    assert cfg.token_expire_minutes == 120
    assert cfg.issuer == "https://auth.hexastack.io"
    assert cfg.audience == "hexastack-backend"
    assert cfg.provider == "memory"
    assert cfg.hasher == "memory"
    assert cfg.enabled is False


def test_register_auth_config():
    reg = ConfigRegistry()
    register_auth_config(reg)
    assert "auth" in reg
    schema = reg.get("auth")
    assert schema is HexastackAuthConfig
