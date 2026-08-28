"""CLI MCP devtools commands."""

from __future__ import annotations

import importlib.util

import typer

__all__ = [
    "add_mcp_commands",
]


def add_mcp_commands(app: typer.Typer) -> None:
    """Register 'mcp' subcommand group for AI agent integration."""
    if importlib.util.find_spec("hexastack_mcp") is None:
        return

    mcp_app = typer.Typer(
        name="mcp",
        help="Model Context Protocol (MCP) AI agent tools and server.",
        no_args_is_help=True,
    )
    app.add_typer(mcp_app, name="mcp")

    @mcp_app.command(
        name="run",
        help="Launch the MCP server in stdio mode (for Claude, Cursor, Gemini, Antigravity).",
    )
    def mcp_run() -> None:
        from mcp.server.fastmcp import FastMCP as McpServer

        import hexastack.application.diagnostics
        from hexastack_core.infra.bootstrap import bootstrap
        from hexastack_mcp.adapters.stdio import run_stdio_server

        runtime = bootstrap(packages_to_scan=[hexastack.application.diagnostics])
        server = runtime.container.resolve(McpServer)
        run_stdio_server(server)

    @mcp_app.command(
        name="config",
        help="Generate MCP JSON configuration for Gemini / Antigravity, Claude Desktop, or Cursor.",
    )
    def mcp_config(
        client: str = typer.Option(
            "antigravity",
            "--client",
            "-c",
            help="Target client: 'antigravity', 'gemini', 'claude', 'cursor'.",
        ),
        server_name: str = typer.Option(
            "hexastack",
            "--name",
            "-n",
            help="Server name in the MCP client config.",
        ),
        command_override: str | None = typer.Option(
            None,
            "--command",
            help="Custom executable command (defaults to 'uv run hexastack mcp run').",
        ),
    ) -> None:
        _exec_mcp_config(client, server_name, command_override)

    @mcp_app.command(
        name="list",
        help="Inspect and list registered MCP tools, prompt templates, and resources.",
    )
    def mcp_list() -> None:
        _exec_mcp_list()


def _exec_mcp_config(
    client: str, server_name: str, command_override: str | None
) -> None:
    import json

    cmd = command_override or "uv"
    args = ["run", "hexastack", "mcp", "run"] if command_override is None else []
    client_key = client.lower().strip()

    if client_key in ("antigravity", "gemini", "agy"):
        config = {
            "mcpServers": {
                server_name: {
                    "command": cmd,
                    "args": args,
                    "env": {
                        "HEXASTACK_AI__PROVIDER": "gemini",
                        "PYTHONUNBUFFERED": "1",
                    },
                }
            }
        }
    elif client_key == "claude":
        config = {
            "mcpServers": {
                server_name: {
                    "command": cmd,
                    "args": args,
                    "env": {
                        "PYTHONUNBUFFERED": "1",
                    },
                }
            }
        }
    else:
        config = {
            "mcpServers": {
                server_name: {
                    "command": cmd,
                    "args": args,
                }
            }
        }

    typer.echo(json.dumps(config, indent=2))


def _exec_mcp_list() -> None:
    from hexastack_mcp.infra.decorators import get_mcp_registry

    registry = get_mcp_registry()
    typer.echo("🤖 [bold cyan]Model Context Protocol (MCP) Capabilities[/bold cyan]\n")

    typer.echo(f"🔧 [bold]Registered Tools ({len(registry.tools)}):[/bold]")
    if not registry.tools:
        typer.echo("   (No tools registered)")
    else:
        for t in registry.tools:
            desc = f" - {t.description}" if t.description else ""
            typer.echo(f"   • [green]{t.name}[/green] ({t.kind}){desc}")
    typer.echo("")

    typer.echo(f"📝 [bold]Prompts ({len(registry.prompts)}):[/bold]")
    if not registry.prompts:
        typer.echo("   (No prompt templates registered)")
    else:
        for p in registry.prompts:
            typer.echo(f"   • [yellow]{p.name}[/yellow]: {p.description}")
    typer.echo("")

    typer.echo(f"📦 [bold]Resources ({len(registry.resources)}):[/bold]")
    if not registry.resources:
        typer.echo("   (No resources registered)")
    else:
        for r in registry.resources:
            typer.echo(f"   • [magenta]{r.name}[/magenta] ({r.uri})")
