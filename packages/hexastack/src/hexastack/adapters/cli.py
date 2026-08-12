import importlib.util
from pathlib import Path

import typer
from hexastack_cli.infra.decorators import (
    cli_command,
    cli_group,
    cli_query,
)
from hexastack_core.domain.exceptions import MissingDependencyError

from hexastack.domain.diagnostics import (
    GetSystemInfoQuery,
    InspectRegistryQuery,
    PingDemoCommand,
)


@cli_group("inspect", help="Introspect registered CQRS handlers, routes, and config")
class InspectGroupDocs:
    pass


@cli_group("demo", help="Interactive demonstration commands")
class DemoGroupDocs:
    pass


# Decorate diagnostics domain models with CLI exposure metadata
cli_query(
    "info",
    aliases=["doctor", "status"],
    help="Display installed Hexastack packages and optional dependency statuses.",
)(GetSystemInfoQuery)

cli_query(
    "registry",
    group="inspect",
    aliases=["handlers"],
    help="Display registered CQRS commands, queries, and configurations.",
)(InspectRegistryQuery)

cli_command(
    "ping",
    group="demo",
    aliases=["/ping"],
    help="Send a test ping command through the CQRS execution pipeline.",
)(PingDemoCommand)


def add_serve_command(app: typer.Typer) -> None:
    """Register 'serve' command to launch the local FastAPI dev server using Uvicorn.

    Args:
        app: Target Typer application instance.

    Returns:
        None.

    Raises:
        None.
    """

    @app.command(
        name="serve",
        help="Launch the Hexastack local development server (requires hexastack[web]).",
    )
    def serve(
        host: str = typer.Option(
            "127.0.0.1", "--host", "-h", help="Bind host address."
        ),
        port: int = typer.Option(8000, "--port", "-p", help="Bind port number."),
        reload: bool = typer.Option(
            True, "--reload/--no-reload", help="Enable live reloading."
        ),
    ) -> None:
        if importlib.util.find_spec("uvicorn") is None:
            raise MissingDependencyError(
                "uvicorn is required to run the local server. "
                "Install via 'pip install hexastack[web]' or 'pip install uvicorn[standard]'."
            )

        if importlib.util.find_spec("fastapi") is None:
            raise MissingDependencyError(
                "fastapi is required to run the local server. "
                "Install via 'pip install hexastack[fastapi]'."
            )

        import uvicorn

        from hexastack.adapters.fastapi import create_demo_app

        demo_app = create_demo_app()
        uvicorn.run(demo_app, host=host, port=port, reload=reload)


def add_db_commands(app: typer.Typer) -> None:
    """Register 'db' subcommand group with migration management commands.

    Notes/Architectural Intent:
        All commands guard against missing hexastack-db[migrations] and raise
        a clear MissingDependencyError. The DATABASE_URL env var or --url flag
        always overrides the default SQLite connection URL.

    Args:
        app: Target Typer application instance.

    Returns:
        None.

    Raises:
        None.
    """
    if importlib.util.find_spec("hexastack_db") is None:
        return

    db_app = typer.Typer(
        name="db",
        help="Database migration management (requires hexastack[db,migrations]).",
        no_args_is_help=True,
    )
    app.add_typer(db_app, name="db")

    def _require_migrations() -> None:
        if importlib.util.find_spec("alembic") is None:
            raise MissingDependencyError(
                "alembic is required for migration commands. "
                "Install via 'pip install hexastack-db[migrations]'."
            )

    def _get_config(migrations_dir: str, url: str | None):
        import os

        from hexastack_db.infra.migrations import get_alembic_config

        db_url = url or os.environ.get("DATABASE_URL", "sqlite:///hexastack.db")
        return get_alembic_config(
            migrations_dir=migrations_dir,
            db_url=db_url,
        )

    @db_app.command(name="init", help="Scaffold a new migrations directory.")
    def db_init(
        directory: str = typer.Argument(
            "migrations", help="Path to create the migrations directory."
        ),
        url: str | None = typer.Option(
            None, "--url", help="Database URL (overrides DATABASE_URL env var)."
        ),
    ) -> None:
        _require_migrations()
        import os

        from hexastack_db.infra.config import HexastackDatabaseConfig
        from hexastack_db.infra.migrations import init_migrations

        db_url = url or os.environ.get("DATABASE_URL", "sqlite:///hexastack.db")
        cfg = HexastackDatabaseConfig(url=db_url)
        try:
            init_migrations(migrations_dir=directory, db_config=cfg)
            typer.echo(f"Initialized migrations directory: {Path(directory).resolve()}")
        except FileExistsError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)

    @db_app.command(name="upgrade", help="Upgrade the database to a revision.")
    def db_upgrade(
        directory: str = typer.Option(
            "migrations", "--dir", help="Migrations directory."
        ),
        revision: str = typer.Argument("head", help="Target revision (default: head)."),
        url: str | None = typer.Option(
            None, "--url", help="Database URL (overrides DATABASE_URL env var)."
        ),
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import run_upgrade

        run_upgrade(_get_config(directory, url), revision)

    @db_app.command(name="downgrade", help="Downgrade the database to a revision.")
    def db_downgrade(
        directory: str = typer.Option(
            "migrations", "--dir", help="Migrations directory."
        ),
        revision: str = typer.Argument("-1", help="Target revision (default: -1)."),
        url: str | None = typer.Option(
            None, "--url", help="Database URL (overrides DATABASE_URL env var)."
        ),
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import run_downgrade

        run_downgrade(_get_config(directory, url), revision)

    @db_app.command(name="revision", help="Generate a new migration revision.")
    def db_revision(
        message: str = typer.Argument(..., help="Short description of the migration."),
        directory: str = typer.Option(
            "migrations", "--dir", help="Migrations directory."
        ),
        no_autogenerate: bool = typer.Option(
            False, "--no-autogenerate", help="Disable schema autogeneration."
        ),
        url: str | None = typer.Option(
            None, "--url", help="Database URL (overrides DATABASE_URL env var)."
        ),
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import run_revision

        run_revision(
            _get_config(directory, url),
            message=message,
            autogenerate=not no_autogenerate,
        )

    @db_app.command(name="current", help="Show the current applied revision.")
    def db_current(
        directory: str = typer.Option(
            "migrations", "--dir", help="Migrations directory."
        ),
        url: str | None = typer.Option(
            None, "--url", help="Database URL (overrides DATABASE_URL env var)."
        ),
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import run_current

        run_current(_get_config(directory, url))

    @db_app.command(name="history", help="Show migration revision history.")
    def db_history(
        directory: str = typer.Option(
            "migrations", "--dir", help="Migrations directory."
        ),
        url: str | None = typer.Option(
            None, "--url", help="Database URL (overrides DATABASE_URL env var)."
        ),
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import run_history

        run_history(_get_config(directory, url))

    @db_app.command(
        name="stamp",
        help="Stamp the database at a revision without running migrations.",
    )
    def db_stamp(
        revision: str = typer.Argument(
            "head", help="Revision to stamp (default: head)."
        ),
        directory: str = typer.Option(
            "migrations", "--dir", help="Migrations directory."
        ),
        url: str | None = typer.Option(
            None, "--url", help="Database URL (overrides DATABASE_URL env var)."
        ),
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import stamp

        stamp(_get_config(directory, url), revision)


__all__ = [
    "DemoGroupDocs",
    "InspectGroupDocs",
    "add_db_commands",
    "add_serve_command",
]
