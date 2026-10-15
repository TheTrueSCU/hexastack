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
    step_ch02_1_scaffold_sqlite_service,
    step_ch02_2_inspect_db_commands,
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

            # Record Chapter 2 Part 1: Scaffold SQLite persistent service
            step_ch02_1_scaffold_sqlite_service(narrator, record=True)
            seg1 = narrator.checkpoint_segment("part1-sqlite")

            # Record Chapter 2 Part 2: Inspect Alembic database migration commands
            step_ch02_2_inspect_db_commands(narrator, record=True)
            narrator.step(
                "SQLite persistence configured with decoupled SQLAlchemy adapter"
            )
            seg2 = narrator.checkpoint_segment("part2-migrations")
            artifacts = narrator.finish()

            segment_count = narrator._segment_count
            assert segment_count == 2

            if os.environ.get("RECORD_DEMO") == "1":
                seg1_vtt = seg1.get("vtt")
                has_seg1_vtt = seg1_vtt is not None and seg1_vtt.exists()
                assert has_seg1_vtt is True

                seg1_webm = seg1.get("webm")
                has_seg1_webm = seg1_webm is not None and seg1_webm.exists()
                assert has_seg1_webm is True

                seg2_vtt = seg2.get("vtt")
                has_seg2_vtt = seg2_vtt is not None and seg2_vtt.exists()
                assert has_seg2_vtt is True

                seg2_webm = seg2.get("webm")
                has_seg2_webm = seg2_webm is not None and seg2_webm.exists()
                assert has_seg2_webm is True

                has_seg1_key = "todo-ch02-cli-demo-part1-sqlite_webm" in artifacts
                assert has_seg1_key is True

                has_seg2_key = "todo-ch02-cli-demo-part2-migrations_webm" in artifacts
                assert has_seg2_key is True
        finally:
            os.chdir(orig_cwd)
