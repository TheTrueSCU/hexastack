import tempfile
from pathlib import Path

from pydantic import BaseModel

from hexastack_core.infra.registries.config import ConfigRegistry


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


def test_config_registry_layered_chainmap_resolution(tmp_path: Path):
    """Verify collections.ChainMap provides layered precedence: overrides > env > toml."""
    registry = ConfigRegistry()
    registry.register_config_section("custom", CustomSection)

    toml_file = tmp_path / "config.toml"
    toml_content = """
    [hexastack]
    environment = "dev"
    app_name = "base-app"
    debug = false

    [hexastack.custom]
    timeout = 10
    """
    toml_file.write_text(toml_content, encoding="utf-8")

    # Layer 2: Env vars
    env_vars = {
        "HEXASTACK_CORE__ENVIRONMENT": "staging",
        "HEXASTACK_CUSTOM__TIMEOUT": "45",
    }

    # Layer 1: Overrides (highest precedence)
    overrides = {
        "hexastack": {"debug": True},
        "custom": {"timeout": 99},
    }

    config = registry.load_config_layered(
        raw_file_path=toml_file,
        overrides=overrides,
        env_vars=env_vars,
    )

    # Overrides win for debug & timeout
    debug_val = config._core.debug
    assert debug_val is True

    custom = config.get_section("custom", CustomSection)
    timeout_val = custom.timeout
    assert timeout_val == 99

    # Env wins for environment (not in overrides, but in env)
    env_val = config._core.environment
    assert env_val == "staging"

    # TOML wins for app_name (not in overrides, not in env)
    app_name_val = config._core.app_name
    assert app_name_val == "base-app"
