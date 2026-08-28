"""CLI commands for 'hexastack new' archetypes.

Notes/Architectural Intent:
    Provides subcommands for scaffolding archetypes (web-api, minimal, event-driven,
    mcp-agent, grpc-service, graphql-service, enterprise).
"""

from __future__ import annotations

import typer

from hexastack.application.scaffolding.generator import scaffold_project

__all__ = [
    "create_new_app",
]


def create_new_app() -> typer.Typer:
    """Create and configure the 'new' Typer command group.

    Returns:
        Configured Typer instance for 'hexastack new'.
    """
    new_app = typer.Typer(
        name="new",
        help="Scaffold a new Hexagonal microservice project.",
        no_args_is_help=True,
        invoke_without_command=True,
    )

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
            include_release=True,
            include_openssf=True,
        )
        typer.echo(
            f"🎉 Created new Full-Featured Enterprise Hexastack project at '{target_path}'"
        )
        typer.echo(f"   Next steps:\n     cd {name}\n     uv sync\n     uv run pytest")

    return new_app
