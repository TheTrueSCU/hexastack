"""Feature demo recordings for Tutorial Chapter 5: AI MCP Tools & Feature Flags."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import typer
from playwright.sync_api import Page, expect

from hexastack.adapters.cli.scaffolding.commands import add_scaffold_commands
from hexastack_cli.testing.narrator import CliNarrator
from hexastack_fastapi.testing.recorder import DemoNarrator
from hexastack_fastapi.testing.server import ephemeral_server


@pytest.mark.demo
@pytest.mark.ch05
def test_todo_ch05_cli_demo() -> None:
    """Record Chapter 5 AI MCP & Feature Flags setup in terminal video."""
    app = typer.Typer(name="hexastack")
    add_scaffold_commands(app)
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

            # Step 1: Scaffold MCP agent service
            narrator.step("Tutorial Chapter 5: Gated AI Agent & MCP Tool Server")
            res_new = narrator.run_command(["new", "mcp-agent", "todo-mcp-assistant"])
            assert res_new.exit_code == 0
            assert Path(tmpdir, "todo-mcp-assistant", "pyproject.toml").exists()

            # Step 2: Show CLI help
            narrator.step("Exposing CQRS Commands to LLMs via Model Context Protocol")
            narrator.run_command(["new", "--help"])

            # Step 3: Conclude CLI section
            narrator.step(
                "Autonomous AI Assistant generates daily morning executive briefings"
            )
            artifacts = narrator.finish()

            if os.environ.get("RECORD_DEMO") == "1":
                assert "vtt" in artifacts and artifacts["vtt"].exists()
                assert "webm" in artifacts and artifacts["webm"].exists()
        finally:
            os.chdir(orig_cwd)


TODO_CH05_FACTORY = """
import uvicorn
from todo_app.entrypoints.ch05_ai_mcp import build_app
app, _ = build_app(db_url="sqlite:///todos_ch05_demo.db")
uvicorn.run(app, host="127.0.0.1", port={port})
"""


@pytest.mark.e2e
@pytest.mark.demo
@pytest.mark.ch05
def test_todo_ch05_browser_demo(page: Page, demo: DemoNarrator) -> None:
    """Record Chapter 5 interactive browser experience (MCP & Feature Flags)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = f"examples/todo-app/src:{env.get('PYTHONPATH', '')}"

    with ephemeral_server(app_factory_code=TODO_CH05_FACTORY, env=env) as server_url:
        demo.output_name = "todo-ch05-browser-demo"

        # 1. Open Swagger Docs
        docs_url = f"{server_url}/docs"
        demo.goto(docs_url, caption="Tutorial 5: AI-Enabled To-Do Service & MCP Tools")

        # 2. Verify endpoints
        post_endpoint = page.locator(".opblock-post").first
        expect(post_endpoint).to_be_visible()

        # 3. Expand POST /todos
        demo.click(post_endpoint, caption="AI Agent creating tasks via CQRS pipeline")
        page.wait_for_timeout(800)

        # 4. Expand GET /todos
        get_endpoint = page.locator(".opblock-get").first
        if get_endpoint.is_visible():
            demo.click(
                get_endpoint, caption="Retrieving active tasks for AI morning briefing"
            )
            page.wait_for_timeout(800)

        # 5. Finish demo
        demo.step("Chapter 5 completed: MCP tool exposure & AI briefing verified!")
        page.wait_for_timeout(1200)
        demo.finish()
