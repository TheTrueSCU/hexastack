"""Feature demo recordings for Tutorial Chapter 5: AI Assistant & MCP Tools."""

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
    step_ch03_configure_jwt_auth,
    step_ch04_configure_events_outbox,
    step_ch05_configure_ai_mcp,
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
@pytest.mark.ch05
def test_todo_ch05_cli_demo() -> None:
    """Record Chapter 5 MCP AI Tools (replaying Chapters 1-4 silently)."""
    app = _build_cli_app()
    repo_root = Path.cwd()

    with tempfile.TemporaryDirectory() as tmpdir:
        orig_cwd = Path.cwd()
        try:
            os.chdir(tmpdir)
            narrator = CliNarrator(
                app,
                output_name="todo-ch05-cli-demo",
                output_dir=repo_root / "docs" / "assets" / "demos",
            )

            # Replay steps 1-4 silently
            step_ch01_scaffold_minimal(narrator, record=False)
            step_ch02_configure_sqlite(narrator, record=False)
            step_ch03_configure_jwt_auth(narrator, record=False)
            step_ch04_configure_events_outbox(narrator, record=False)

            # Record step 5
            step_ch05_configure_ai_mcp(narrator, record=True)

            narrator.step("Model Context Protocol tools exposed to AI agents")
            artifacts = narrator.finish()

            if os.environ.get("RECORD_DEMO") == "1":
                assert "vtt" in artifacts and artifacts["vtt"].exists()
                assert "webm" in artifacts and artifacts["webm"].exists()
        finally:
            os.chdir(orig_cwd)
