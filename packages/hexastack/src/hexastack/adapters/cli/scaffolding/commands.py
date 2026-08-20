"""CLI command definitions for project scaffolding and template subcommands.

Notes/Architectural Intent:
    Supports both `hexastack new <name> --template <template>` and template subcommands
    like `hexastack new web-api <name>` or `hexastack new event-driven <name>`.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import typer

from hexastack.application.scaffolding.generator import (
    TemplateType,
    scaffold_project,
)

__all__ = [
    "add_scaffold_commands",
]


def add_scaffold_commands(app: typer.Typer) -> None:
    """Register 'new' and 'init' project scaffolding commands with template subcommands.

    Args:
        app: Target Typer application instance.
    """
    new_app = typer.Typer(
        name="new",
        help="Scaffold a new Hexagonal microservice project.",
        no_args_is_help=True,
        invoke_without_command=True,
    )
    app.add_typer(new_app, name="new")

    @new_app.command(
        name="web-api",
        help="Scaffold a RESTful Web API microservice (FastAPI + UoW + DevTools UI).",
    )
    def new_web_api(
        name: str = typer.Argument(..., help="Name of the new microservice project."),
        description: str = typer.Option(
            "A modern RESTful microservice powered by Hexastack.",
            "--description",
            "-d",
            help="Project description.",
        ),
        db: str = typer.Option(
            "in-memory",
            "--db",
            help="Database driver: in-memory, sqlite, postgres.",
        ),
    ) -> None:
        target_path = scaffold_project(
            name=name,
            template="web-api",
            description=description,
            db_type=db,
        )
        typer.echo(f"🎉 Created new Hexastack Web API project at '{target_path}'")
        typer.echo(f"   Next steps:\n     cd {name}\n     uv sync\n     uv run pytest")

    @new_app.command(
        name="minimal",
        help="Scaffold a lightweight CLI or worker service (Core + CQRS + Logging).",
    )
    def new_minimal(
        name: str = typer.Argument(..., help="Name of the new microservice project."),
        description: str = typer.Option(
            "A lightweight Hexastack service.",
            "--description",
            "-d",
            help="Project description.",
        ),
    ) -> None:
        target_path = scaffold_project(
            name=name,
            template="minimal",
            description=description,
        )
        typer.echo(f"🎉 Created new Minimal Hexastack project at '{target_path}'")
        typer.echo(f"   Next steps:\n     cd {name}\n     uv sync\n     uv run pytest")

    @new_app.command(
        name="event-driven",
        help="Scaffold an Event-Driven service with CloudEvents and Transactional Outbox.",
    )
    def new_event_driven(
        name: str = typer.Argument(..., help="Name of the new microservice project."),
        description: str = typer.Option(
            "An event-driven Hexastack service.",
            "--description",
            "-d",
            help="Project description.",
        ),
    ) -> None:
        target_path = scaffold_project(
            name=name,
            template="event-driven",
            description=description,
            include_events=True,
        )
        typer.echo(f"🎉 Created new Event-Driven Hexastack project at '{target_path}'")
        typer.echo(f"   Next steps:\n     cd {name}\n     uv sync\n     uv run pytest")

    @new_app.command(
        name="mcp-agent",
        help="Scaffold an AI Model Context Protocol (MCP) server & agent tools service.",
    )
    def new_mcp_agent(
        name: str = typer.Argument(..., help="Name of the new microservice project."),
        description: str = typer.Option(
            "An MCP AI agent tools service powered by Hexastack.",
            "--description",
            "-d",
            help="Project description.",
        ),
    ) -> None:
        target_path = scaffold_project(
            name=name,
            template="mcp-agent",
            description=description,
            include_mcp=True,
        )
        typer.echo(f"🎉 Created new MCP Agent Hexastack project at '{target_path}'")
        typer.echo(f"   Next steps:\n     cd {name}\n     uv sync\n     uv run pytest")

    @app.command(
        name="init",
        help="Initialize a new Hexastack microservice in the current working directory.",
    )
    def init(
        name: str = typer.Option(
            None,
            "--name",
            "-n",
            help="Project name (defaults to current directory name).",
        ),
        template: str = typer.Option(
            "web-api",
            "--template",
            "-t",
            help="Project template: minimal, web-api, event-driven, mcp-agent, enterprise.",
        ),
    ) -> None:
        current_dir = Path.cwd()
        proj_name = name or current_dir.name
        target_path = scaffold_project(
            name=proj_name,
            template=cast("TemplateType", template),
            output_dir=current_dir.parent,
        )
        typer.echo(f"🎉 Initialized Hexastack project in '{target_path}'")
