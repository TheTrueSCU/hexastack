from hexastack_auth.domain.config import (
    HexastackAuthConfig,
    OpaConfig,
    OpenFgaConfig,
    SpiffeConfig,
)


def test_hexastack_auth_config_defaults():
    cfg = HexastackAuthConfig()
    assert cfg.algorithm == "HS256"
    assert cfg.token_expire_minutes == 60
    assert cfg.provider == "jwt"
    assert cfg.hasher == "pbkdf2"
    assert isinstance(cfg.opa, OpaConfig)
    assert isinstance(cfg.openfga, OpenFgaConfig)
    assert isinstance(cfg.spiffe, SpiffeConfig)
