"""CLI command definitions for demo showcase and diagnostics.

Notes/Architectural Intent:
    Provides subcommands for inspecting registries, running diagnostic queries,
    and launching interactive developer servers.
"""

from __future__ import annotations

import importlib.util
import os
from typing import Any

import typer

from hexastack_core.domain.exceptions import MissingDependencyError

__all__ = [
    "add_db_commands",
]


def add_db_commands(app: typer.Typer) -> None:
    """Register 'db' subcommand group with migration management commands."""
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

    def _get_config(migrations_dir: str, url: str | None) -> Any:
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
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import init_migrations

        init_migrations(directory)

    @db_app.command(
        name="migrate", help="Apply pending database migrations (upgrade to head)."
    )
    def db_migrate(
        directory: str = typer.Option(
            "migrations", "--dir", help="Migrations directory."
        ),
        revision: str = typer.Option("head", "--revision", help="Target revision."),
        url: str | None = typer.Option(
            None, "--url", help="Database URL (overrides DATABASE_URL env var)."
        ),
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import run_upgrade

        run_upgrade(_get_config(directory, url), revision=revision)

    @db_app.command(
        name="check",
        help="Verify there is no unapplied schema drift or missing migrations (Alembic check).",
    )
    def db_check(
        directory: str = typer.Option(
            "migrations", "--dir", help="Migrations directory."
        ),
        url: str | None = typer.Option(
            None, "--url", help="Database URL (overrides DATABASE_URL env var)."
        ),
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import run_check

        try:
            run_check(_get_config(directory, url))
            typer.echo("✅ Database schema and migration revisions are fully in sync.")
        except Exception as e:
            typer.echo(f"❌ Schema drift detected: {e}")
            raise typer.Exit(code=1) from e

    @db_app.command(name="revision", help="Generate a new migration revision script.")
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
