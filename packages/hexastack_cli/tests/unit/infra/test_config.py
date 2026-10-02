from hexastack_cli.infra.config import (
    HexastackCliConfig,
    register_cli_config,
)
from hexastack_core.infra.registries.config import ConfigRegistry


def test_cli_config_custom():
    cfg = HexastackCliConfig.model_validate(
        {
            "app_name": "custom-cli",
            "help_text": "Custom Tool",
            "auto_register_commands": False,
        }
    )

    assert cfg.app_name == "custom-cli"
    assert cfg.help_text == "Custom Tool"
    assert cfg.auto_register_commands is False


def test_cli_config_defaults():
    cfg = HexastackCliConfig()

    assert cfg.app_name == "hexastack"
    assert cfg.help_text == "Hexastack CLI Application"
    assert cfg.auto_register_commands is True
    assert cfg.rich_markup is True
    assert cfg.show_exceptions is False


def test_register_cli_config():
    reg = ConfigRegistry()
    register_cli_config(reg)

    assert "cli" in reg
    assert reg.get("cli") == HexastackCliConfig
