import tempfile
from pathlib import Path

from hexastack_core.infra.registries.config import ConfigRegistry
from pydantic import BaseModel


class CustomSection(BaseModel):
    timeout: int = 30


def test_config_registry_registration_and_loading():
    registry = ConfigRegistry()
    registry.register_config_section("custom", CustomSection)

    toml_content = """
    [hexastack]
    environment = "staging"
    app_name = "sample-app"
    debug = true

    [hexastack.custom]
    timeout = 60
    """

    with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as tmp:
        tmp.write(toml_content)
        tmp_path = tmp.name

    try:
        config = registry.load_config_toml(Path(tmp_path))
        assert config._core.environment == "staging"
        assert config._core.app_name == "sample-app"
        assert config._core.debug is True

        custom = config.get_section("custom", CustomSection)
        assert custom.timeout == 60
    finally:
        Path(tmp_path).unlink(missing_ok=True)
