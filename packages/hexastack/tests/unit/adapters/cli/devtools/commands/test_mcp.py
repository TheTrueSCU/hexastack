"""Unit tests for devtools mcp commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.mcp import add_mcp_commands


def test_mcp_commands():
    app = typer.Typer()
    add_mcp_commands(app)
    runner = CliRunner()
    res = runner.invoke(app, ["mcp", "--help"])
    assert res.exit_code == 0

    res_list = runner.invoke(app, ["mcp", "list"])
    assert res_list.exit_code == 0
    assert "Model Context Protocol" in res_list.output

    for client in ["claude", "cursor", "gemini", "antigravity"]:
        res_cfg = runner.invoke(app, ["mcp", "config", "-c", client])
        assert res_cfg.exit_code == 0

    from unittest.mock import patch

    with patch("hexastack_mcp.adapters.stdio.run_stdio_server"):
        res_run = runner.invoke(app, ["mcp", "run"])
        assert res_run.exit_code == 0
