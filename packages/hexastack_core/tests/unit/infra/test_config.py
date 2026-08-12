import pytest
from hexastack_core.infra.config import (
    HexastackConfig,
    HexastackConfigError,
    HexastackCoreConfig,
)
from pydantic import BaseModel


class CustomSection(BaseModel):
    key: str
    value: int


class OtherSection(BaseModel):
    flag: bool


def test_hexastack_config_get_section_success():
    core = HexastackCoreConfig(environment="prod", app_name="test-app", debug=True)
    custom = CustomSection(key="database", value=5432)
    config = HexastackConfig(core=core, sections={"custom": custom})

    retrieved = config.get_section("custom", CustomSection)
    assert retrieved == custom
    assert retrieved.key == "database"
    assert retrieved.value == 5432


def test_hexastack_config_missing_section_raises_error():
    core = HexastackCoreConfig()
    config = HexastackConfig(core=core, sections={})

    with pytest.raises(HexastackConfigError) as exc_info:
        config.get_section("missing", CustomSection)

    assert "Config section 'missing' not registered." in str(exc_info.value)


def test_hexastack_config_invalid_type_raises_error():
    core = HexastackCoreConfig()
    custom = CustomSection(key="database", value=5432)
    config = HexastackConfig(core=core, sections={"custom": custom})

    with pytest.raises(HexastackConfigError) as exc_info:
        config.get_section("custom", OtherSection)

    assert "Section 'custom' is not of type 'OtherSection'" in str(exc_info.value)
