"""CLI command for 'hexastack init' interactive questionnaire wizard.

Notes/Architectural Intent:
    Provides interactive Rich wizard and CLI flags for bootstrapping new microservices.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from hexastack.application.scaffolding.generator import scaffold_project

__all__ = [
    "add_init_command",
]


def add_init_command(app: typer.Typer) -> None:
    """Register 'init' command with Typer application instance."""

    @app.command(
        name="init",
        help="Initialize a new Hexastack microservice in the current working directory.",
    )
    def init(
        name: str | None = typer.Option(
            None,
            "--name",
            "-n",
            help="Project name (defaults to current directory name).",
        ),
        template: str | None = typer.Option(
            None,
            "--template",
            "-t",
            help="Project template: minimal, web-api, event-driven, mcp-agent, enterprise.",
        ),
        db: str | None = typer.Option(
            None,
            "--db",
            help="Database driver: in-memory, sqlite, postgres.",
        ),
        interactive: bool = typer.Option(
            False,
            "--interactive",
            "-i",
            help="Prompt with interactive questionnaire wizard.",
        ),
        with_release: bool = typer.Option(
            False,
            "--with-release",
            help="Include automated PyPI release & SBOM workflow (.github/workflows/release.yml, CHANGELOG.md).",
        ),
        with_openssf: bool = typer.Option(
            False,
            "--with-openssf",
            help="Include OpenSSF security & governance starter (.github/workflows/scorecard.yml, SECURITY.md, GOVERNANCE.md).",
        ),
    ) -> None:
        current_dir = Path.cwd()
        proj_name = name or current_dir.name

        selected_template = template or "web-api"
        selected_db = db or "in-memory"
        include_events = False
        include_mcp = False
        include_release = with_release
        include_openssf = with_openssf

        # If interactive mode requested or no template explicitly specified and running in a tty
        if interactive or (template is None and sys.stdin.isatty()):
            from rich.console import Console
            from rich.panel import Panel
            from rich.prompt import Confirm, Prompt

            console = Console()
            console.print(
                Panel.fit(
                    "[bold cyan]Hexastack Microservice Initialization Wizard[/bold cyan]\n"
                    "[dim]Scaffold production-grade Hexagonal microservices with Day-1 CI/CD & Governance[/dim]",
                    border_style="cyan",
                )
            )

            proj_name = Prompt.ask("Project name", default=proj_name)
            selected_template = Prompt.ask(
                "Select architecture template",
                choices=[
                    "web-api",
                    "event-driven",
                    "mcp-agent",
                    "grpc-service",
                    "graphql-service",
                    "minimal",
                    "enterprise",
                ],
                default=selected_template,
            )
            selected_db = Prompt.ask(
                "Select database driver",
                choices=["in-memory", "sqlite", "postgres"],
                default=selected_db,
            )
            include_events = Confirm.ask(
                "Enable transactional outbox & CloudEvents 1.0?",
                default=(selected_template in ("event-driven", "enterprise")),
            )
            include_mcp = Confirm.ask(
                "Enable Model Context Protocol (MCP) AI agent tools?",
                default=(selected_template in ("mcp-agent", "enterprise")),
            )
            include_release = Confirm.ask(
                "Configure automated release & SBOM generation workflow?",
                default=with_release or (selected_template == "enterprise"),
            )
            include_openssf = Confirm.ask(
                "Include OpenSSF security scorecard and governance starter pack?",
                default=with_openssf or (selected_template == "enterprise"),
            )

        target_path = scaffold_project(
            name=proj_name,
            template=selected_template,
            db_type=selected_db,
            include_events=include_events,
            include_mcp=include_mcp,
            include_release=include_release,
            include_openssf=include_openssf,
            output_dir=current_dir.parent,
        )

        typer.echo(f"🎉 Initialized Hexastack project in '{target_path}'")
        typer.echo(
            f"   Next steps:\n     cd {proj_name}\n     uv sync\n     uv run pytest"
        )
