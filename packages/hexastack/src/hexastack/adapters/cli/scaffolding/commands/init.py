"""CLI command for 'hexastack init' interactive questionnaire wizard.

Notes/Architectural Intent:
    Provides interactive Questionary wizard with arrow navigation, multi-select checklist,
    and CLI flags for bootstrapping new microservices with Day-1 AI guardrails.
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
        with_qual: bool = typer.Option(
            True,
            "--qual/--no-qual",
            help="Include hexastack-qual quality governance and scorecard adapter.",
        ),
        with_agents: bool = typer.Option(
            True,
            "--agents/--no-agents",
            help="Materialize turnkey universal .agents/ AI guardrails hub.",
        ),
        with_mutation: bool = typer.Option(
            True,
            "--mutation/--no-mutation",
            help="Configure pytest-gremlins mutation testing baseline.",
        ),
        with_sentry: bool = typer.Option(
            False,
            "--sentry/--no-sentry",
            help="Configure Sentry error tracking & distributed tracing.",
        ),
    ) -> None:
        current_dir = Path.cwd()
        proj_name = name or current_dir.name

        selected_template = template or "web-api"
        selected_db = db or "in-memory"

        # If interactive mode requested or no template explicitly specified and running in a tty
        if interactive or (template is None and sys.stdin.isatty()):
            import questionary
            from rich.console import Console
            from rich.panel import Panel

            console = Console()
            console.print(
                Panel.fit(
                    "[bold cyan]Hexastack Microservice Initialization Wizard[/bold cyan]\n"
                    "[dim]Scaffold production-grade Hexagonal microservices with Day-1 CI/CD & AI Guardrails[/dim]",
                    border_style="cyan",
                )
            )

            prompt_name = questionary.text("Project name:", default=proj_name).ask()
            if prompt_name:
                proj_name = prompt_name

            prompt_template = questionary.select(
                "Select architecture template:",
                choices=[
                    questionary.Choice(
                        "web-api (RESTful FastAPI + DevTools UI + SQLite/In-Memory)",
                        value="web-api",
                    ),
                    questionary.Choice(
                        "event-driven (CloudEvents 1.0 + Transactional Outbox + NATS/Kafka)",
                        value="event-driven",
                    ),
                    questionary.Choice(
                        "mcp-agent (Model Context Protocol AI Agent Tools & Servers)",
                        value="mcp-agent",
                    ),
                    questionary.Choice(
                        "grpc-service (High-Performance gRPC + Protobuf Contracts)",
                        value="grpc-service",
                    ),
                    questionary.Choice(
                        "graphql-service (Strawberry GraphQL Data Gateway)",
                        value="graphql-service",
                    ),
                    questionary.Choice(
                        "minimal (Lightweight Core + CQRS + Logging)",
                        value="minimal",
                    ),
                    questionary.Choice(
                        "enterprise (All Modules: FastAPI, gRPC, GraphQL, MCP, Events)",
                        value="enterprise",
                    ),
                ],
                default=selected_template,
            ).ask()
            if prompt_template:
                selected_template = prompt_template

            prompt_db = questionary.select(
                "Select database driver:",
                choices=[
                    questionary.Choice(
                        "in-memory (Fast In-Memory Repository for prototypes & tests)",
                        value="in-memory",
                    ),
                    questionary.Choice(
                        "sqlite (Local File/Memory SQLite with SQLAlchemy)",
                        value="sqlite",
                    ),
                    questionary.Choice(
                        "postgres (Async PostgreSQL with UnitOfWork & Connection Pooling)",
                        value="postgres",
                    ),
                ],
                default=selected_db,
            ).ask()
            if prompt_db:
                selected_db = prompt_db

            batteries = (
                questionary.checkbox(
                    "Select batteries & governance features to enable:",
                    choices=[
                        questionary.Choice(
                            "Quality Governance (hexastack-qual & OpenSSF)",
                            checked=with_qual,
                            value="qual",
                        ),
                        questionary.Choice(
                            "AI Agent Guardrails (.agents/ hub, AGENTS.md, GEMINI.md)",
                            checked=with_agents,
                            value="agents",
                        ),
                        questionary.Choice(
                            "Mutation Testing (pytest-gremlins baseline)",
                            checked=with_mutation,
                            value="mutation",
                        ),
                        questionary.Choice(
                            "Transactional Outbox & CloudEvents",
                            checked=(
                                selected_template in ("event-driven", "enterprise")
                            ),
                            value="events",
                        ),
                        questionary.Choice(
                            "Model Context Protocol (MCP) AI Tools",
                            checked=(selected_template in ("mcp-agent", "enterprise")),
                            value="mcp",
                        ),
                        questionary.Choice(
                            "Automated PyPI Release & SBOM Workflow",
                            checked=with_release or (selected_template == "enterprise"),
                            value="release",
                        ),
                        questionary.Choice(
                            "OpenSSF Scorecard & Security Starter Pack",
                            checked=with_openssf or (selected_template == "enterprise"),
                            value="openssf",
                        ),
                        questionary.Choice(
                            "Sentry Error Tracking & Distributed Tracing",
                            checked=with_sentry,
                            value="sentry",
                        ),
                    ],
                ).ask()
                or []
            )

            include_qual = "qual" in batteries
            include_agents = "agents" in batteries
            include_mutation = "mutation" in batteries
            include_events = "events" in batteries
            include_mcp = "mcp" in batteries
            include_release = "release" in batteries
            include_openssf = "openssf" in batteries
            include_sentry = "sentry" in batteries
        else:
            include_qual = with_qual
            include_agents = with_agents
            include_mutation = with_mutation
            include_events = selected_template in ("event-driven", "enterprise")
            include_mcp = selected_template in ("mcp-agent", "enterprise")
            include_release = with_release or (selected_template == "enterprise")
            include_openssf = with_openssf or (selected_template == "enterprise")
            include_sentry = with_sentry

        try:
            target_path = scaffold_project(
                name=proj_name,
                template=selected_template,
                db_type=selected_db,
                include_events=include_events,
                include_mcp=include_mcp,
                include_release=include_release,
                include_openssf=include_openssf,
                include_qual=include_qual,
                include_agents=include_agents,
                include_mutation=include_mutation,
                include_sentry=include_sentry,
                target_dir=current_dir,
            )
        except FileExistsError as exc:
            typer.echo(f"❌ Initialization failed: {exc}", err=True)
            raise typer.Exit(code=1) from exc

        typer.echo(f"🎉 Initialized Hexastack project in '{target_path}'")
        typer.echo("   Next steps:\n     uv sync\n     uv run pytest")
