from hexastack_cli.domain.config import HexastackCliConfig


def test_hexastack_cli_config_defaults():
    cfg = HexastackCliConfig()
    assert cfg.app_name == "hexastack"
    assert cfg.version == "0.1.0"
    assert cfg.auto_register_commands is True
    assert cfg.rich_markup is True
