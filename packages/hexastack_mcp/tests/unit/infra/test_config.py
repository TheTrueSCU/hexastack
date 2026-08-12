from pathlib import Path

from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_mcp.infra.config import (
    HexastackMcpConfig,
    register_mcp_config,
)


def test_mcp_config_defaults():
    cfg = HexastackMcpConfig()
    assert cfg.server_name == "Hexastack MCP Server"
    assert cfg.sse_path == "/sse"
    assert cfg.auto_mount_fastapi is True


def test_register_mcp_config(tmp_path: Path):
    reg = ConfigRegistry()
    register_mcp_config(reg)

    cfg_file = tmp_path / "hexastack.toml"
    cfg_file.write_text(
        """
        [hexastack.mcp]
        server_name = "Custom Agent Server"
        sse_path = "/custom_sse"
        auto_mount_fastapi = false
        """,
        encoding="utf-8",
    )
    loaded = reg.load_config_toml(cfg_file)
    mcp_cfg = loaded.get_section("mcp", HexastackMcpConfig)
    assert mcp_cfg is not None
    assert mcp_cfg.server_name == "Custom Agent Server"
    assert mcp_cfg.sse_path == "/custom_sse"
    assert mcp_cfg.auto_mount_fastapi is False
