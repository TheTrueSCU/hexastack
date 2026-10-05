"""Feature demo recordings for Tutorial Chapter 2: SQLite Persistence & Migrations."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import typer

from hexastack.adapters.cli.devtools.commands import (
    add_db_commands,
    add_dev_command,
    add_fastapi_commands,
    add_grpc_commands,
    add_mcp_commands,
    add_outbox_commands,
    add_serve_command,
    add_ui_commands,
)
from hexastack.adapters.cli.scaffolding.commands import add_scaffold_commands
from hexastack_cli.testing.narrator import CliNarrator
from tests.e2e.tutorials.helpers import (
    step_ch01_scaffold_minimal,
    step_ch02_configure_sqlite,
)


def _build_cli_app() -> typer.Typer:
    app = typer.Typer(name="hexastack")
    add_scaffold_commands(app)
    add_serve_command(app)
    add_dev_command(app)
    add_ui_commands(app)
    add_db_commands(app)
    add_fastapi_commands(app)
    add_grpc_commands(app)
    add_mcp_commands(app)
    add_outbox_commands(app)
    return app


@pytest.mark.demo
@pytest.mark.ch02
def test_todo_ch02_cli_demo() -> None:
    """Record Chapter 2 SQLite configuration in terminal video (replaying Chapter 1 silently)."""
    app = _build_cli_app()
    repo_root = Path.cwd()

    with tempfile.TemporaryDirectory() as tmpdir:
        orig_cwd = Path.cwd()
        try:
            os.chdir(tmpdir)
            narrator = CliNarrator(
                app,
                output_name="todo-ch02-cli-demo",
                output_dir=repo_root / "docs" / "assets" / "demos",
            )

            # Replay step 1 silently (no recording)
            step_ch01_scaffold_minimal(narrator, record=False)

            # Record step 2
            step_ch02_configure_sqlite(narrator, record=True)

            narrator.step(
                "SQLite persistence configured with decoupled SQLAlchemy adapter"
            )
            artifacts = narrator.finish()

            if os.environ.get("RECORD_DEMO") == "1":
                assert "vtt" in artifacts and artifacts["vtt"].exists()
                assert "webm" in artifacts and artifacts["webm"].exists()
        finally:
            os.chdir(orig_cwd)
