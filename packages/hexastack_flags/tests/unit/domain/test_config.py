from hexastack_flags.domain.config import HexastackFlagsConfig
from hexastack_flags.domain.models import FeatureFlagProviderType


def test_hexastack_flags_config_defaults():
    cfg = HexastackFlagsConfig()
    assert cfg.provider == FeatureFlagProviderType.IN_MEMORY.value
    assert cfg.host == "localhost"
    assert cfg.port == 8013
    assert cfg.cache is True
    assert cfg.timeout_ms == 5000
