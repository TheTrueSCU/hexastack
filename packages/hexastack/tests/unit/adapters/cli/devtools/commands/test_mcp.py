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

    from unittest.mock import MagicMock, patch

    with patch("hexastack_mcp.adapters.stdio.run_stdio_server"):
        res_run = runner.invoke(app, ["mcp", "run"])
        assert res_run.exit_code == 0

    # Populated MCP tools, prompts, resources branch
    mock_tool = MagicMock(
        name="search_db", kind="tool", description="Searches database"
    )
    mock_tool.name = "search_db"
    mock_prompt = MagicMock(name="summarize", description="Summarize text")
    mock_prompt.name = "summarize"
    mock_res = MagicMock(name="schema_spec", uri="file://schema.json")
    mock_res.name = "schema_spec"

    mock_reg = MagicMock()
    mock_reg.tools = [mock_tool]
    mock_reg.prompts = [mock_prompt]
    mock_reg.resources = [mock_res]

    with patch(
        "hexastack_mcp.infra.decorators.get_mcp_registry", return_value=mock_reg
    ):
        res_pop = runner.invoke(app, ["mcp", "list"])
        assert res_pop.exit_code == 0
        assert "search_db" in res_pop.output
        assert "summarize" in res_pop.output
        assert "schema_spec" in res_pop.output
