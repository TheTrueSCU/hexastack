import pytest
from pydantic import BaseModel

from hexastack_core.domain.config import (
    HexastackConfig,
    HexastackConfigError,
    HexastackCoreConfig,
)


class SampleSection(BaseModel):
    key: str = "value"


def test_hexastack_config_get_section():
    core = HexastackCoreConfig(environment="test", app_name="test-app", debug=True)
    section = SampleSection(key="hello")
    cfg = HexastackConfig(core=core, sections={"sample": section})

    retrieved = cfg.get_section("sample", SampleSection)
    assert retrieved.key == "hello"
    assert cfg._core.environment == "test"
    assert cfg._core.debug is True


def test_hexastack_config_unregistered_section():
    core = HexastackCoreConfig()
    cfg = HexastackConfig(core=core, sections={})

    with pytest.raises(HexastackConfigError, match="not registered"):
        cfg.get_section("missing", SampleSection)


def test_hexastack_config_wrong_type():
    core = HexastackCoreConfig()
    cfg = HexastackConfig(core=core, sections={"sample": core})

    with pytest.raises(HexastackConfigError, match="is not of type"):
        cfg.get_section("sample", SampleSection)
