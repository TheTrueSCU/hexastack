"""CLI command definitions for project scaffolding and template subcommands.

Notes/Architectural Intent:
    Supports both `hexastack new <name> --template <template>` and template subcommands
    like `hexastack new web-api <name>` or `hexastack new event-driven <name>`.
"""

from __future__ import annotations

import sys
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

    @new_app.command(
        name="grpc-service",
        help="Scaffold a high-performance gRPC microservice (Protobuf + Server Reflection).",
    )
    def new_grpc_service(
        name: str = typer.Argument(..., help="Name of the new microservice project."),
        description: str = typer.Option(
            "A high-performance gRPC microservice powered by Hexastack.",
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
            template="grpc-service",
            description=description,
            db_type=db,
            include_grpc=True,
        )
        typer.echo(f"🎉 Created new gRPC Hexastack project at '{target_path}'")
        typer.echo(f"   Next steps:\n     cd {name}\n     uv sync\n     uv run pytest")

    @new_app.command(
        name="graphql-service",
        help="Scaffold a GraphQL data-graph gateway microservice (Strawberry + GraphiQL).",
    )
    def new_graphql_service(
        name: str = typer.Argument(..., help="Name of the new microservice project."),
        description: str = typer.Option(
            "A modern GraphQL microservice powered by Hexastack.",
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
            template="graphql-service",
            description=description,
            db_type=db,
            include_graphql=True,
        )
        typer.echo(f"🎉 Created new GraphQL Hexastack project at '{target_path}'")
        typer.echo(f"   Next steps:\n     cd {name}\n     uv sync\n     uv run pytest")

    @new_app.command(
        name="enterprise",
        help="Scaffold a production Enterprise microservice with all modules enabled.",
    )
    def new_enterprise(
        name: str = typer.Argument(..., help="Name of the new microservice project."),
        description: str = typer.Option(
            "A full-featured enterprise Hexastack microservice.",
            "--description",
            "-d",
            help="Project description.",
        ),
        db: str = typer.Option(
            "sqlite",
            "--db",
            help="Database driver: in-memory, sqlite, postgres.",
        ),
    ) -> None:
        target_path = scaffold_project(
            name=name,
            template="enterprise",
            description=description,
            db_type=db,
            include_events=True,
            include_mcp=True,
            include_grpc=True,
            include_graphql=True,
        )
        typer.echo(
            f"🎉 Created new Full-Featured Enterprise Hexastack project at '{target_path}'"
        )
        typer.echo(f"   Next steps:\n     cd {name}\n     uv sync\n     uv run pytest")

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
    ) -> None:
        current_dir = Path.cwd()
        proj_name = name or current_dir.name

        selected_template = template or "web-api"
        selected_db = db or "in-memory"
        include_events = False
        include_mcp = False

        # If interactive mode requested or no template explicitly specified and running in a tty
        if interactive or (template is None and sys.stdin.isatty()):
            from rich.console import Console
            from rich.prompt import Confirm, Prompt

            console = Console()
            console.print(
                "🧙 [bold cyan]Hexastack Microservice Initialization Wizard[/bold cyan]\n"
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

        target_path = scaffold_project(
            name=proj_name,
            template=cast("TemplateType", selected_template),
            db_type=selected_db,
            include_events=include_events,
            include_mcp=include_mcp,
            output_dir=current_dir.parent,
        )
        typer.echo(f"🎉 Initialized Hexastack project in '{target_path}'")
