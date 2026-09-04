from hexastack_mcp.domain.config import HexastackMcpConfig


def test_hexastack_mcp_config_defaults():
    cfg = HexastackMcpConfig()
    assert cfg.server_name == "Hexastack MCP Server"
    assert cfg.server_version == "0.1.0"
    assert cfg.sse_path == "/sse"
    assert cfg.auto_mount_fastapi is True
