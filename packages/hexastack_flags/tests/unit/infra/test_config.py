"""Unit tests for flags configuration."""

from hexastack_flags.infra.config import HexastackFlagsConfig


def test_flags_config_defaults() -> None:
    cfg = HexastackFlagsConfig()
    assert cfg is not None
