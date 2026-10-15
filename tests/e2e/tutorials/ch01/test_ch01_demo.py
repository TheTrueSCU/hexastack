"""Feature demo recordings for Tutorial Chapter 1: To-Do Microservice."""

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
    step_ch01_1_scaffold_project,
    step_ch01_2_inspect_layout,
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
def test_todo_ch01_cli_demo() -> None:
    """Record Chapter 1 CLI Scaffolding & Setup in rich terminal video."""
    app = _build_cli_app()
    repo_root = Path.cwd()

    with tempfile.TemporaryDirectory() as tmpdir:
        orig_cwd = Path.cwd()
        try:
            os.chdir(tmpdir)
            narrator = CliNarrator(
                app,
                output_name="todo-ch01-cli-demo",
                output_dir=repo_root / "docs" / "assets" / "demos",
            )

            # Step 1: Scaffold microservice with in-memory persistence
            step_ch01_1_scaffold_project(narrator, record=True)
            seg1 = narrator.checkpoint_segment("part1-scaffolding")

            # Step 2: Inspect pure hexagonal architecture CLI layout and help
            step_ch01_2_inspect_layout(narrator, record=True)
            narrator.step("Project scaffolded with zero external dependencies")
            seg2 = narrator.checkpoint_segment("part2-layout")
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

                has_seg1_key = "todo-ch01-cli-demo-part1-scaffolding_webm" in artifacts
                assert has_seg1_key is True

                has_seg2_key = "todo-ch01-cli-demo-part2-layout_webm" in artifacts
                assert has_seg2_key is True
        finally:
            os.chdir(orig_cwd)
