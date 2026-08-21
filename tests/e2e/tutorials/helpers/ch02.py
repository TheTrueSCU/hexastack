"""Chapter 2 step helpers: SQLite Persistence & Migrations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack_cli.testing.narrator import CliNarrator


def step_ch02_1_scaffold_sqlite_service(
    narrator: CliNarrator, *, record: bool = True
) -> None:
    """Ch 2 - Step 1: Scaffold microservice configured for SQLite persistence."""
    narrator.step(
        "Tutorial Chapter 2: Adding SQLite persistence & migrations", record=record
    )
    res = narrator.run_command(
        ["new", "web-api", "todo-sqlite-app", "--db", "sqlite"],
        record=record,
    )
    if res.exit_code != 0:
        raise RuntimeError(
            f"Ch 2 Step 1 failed with exit code {res.exit_code}: {res.output}"
        )


def step_ch02_2_inspect_db_commands(
    narrator: CliNarrator, *, record: bool = True
) -> None:
    """Ch 2 - Step 2: Inspect Alembic database migration CLI commands."""
    narrator.step("Inspecting Alembic database migration commands", record=record)
    narrator.run_command(["db", "--help"], record=record)


def step_ch02_configure_sqlite(narrator: CliNarrator, *, record: bool = True) -> None:
    """Ch 2 Orchestrator: Complete Chapter 2 setup."""
    step_ch02_1_scaffold_sqlite_service(narrator, record=record)
    step_ch02_2_inspect_db_commands(narrator, record=record)
