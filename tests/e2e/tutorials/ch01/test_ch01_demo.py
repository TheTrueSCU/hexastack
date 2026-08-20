"""Feature demo recordings for Tutorial Chapter 1: To-Do Microservice."""

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
def test_todo_ch01_cli_demo() -> None:
    """Record Chapter 1 CLI Scaffolding & Setup in rich terminal video."""
    app = typer.Typer(name="hexastack")
    add_scaffold_commands(app)
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

            # Step 1: Scaffold To-Do microservice
            narrator.step("Tutorial Chapter 1: Scaffolding a To-Do REST microservice")
            res_new = narrator.run_command(
                ["new", "web-api", "todo-app", "--db", "in-memory"]
            )
            assert res_new.exit_code == 0
            assert Path(tmpdir, "todo-app", "pyproject.toml").exists()

            # Step 2: Show directory layout
            narrator.step("Inspecting pure hexagonal architecture layout")
            narrator.run_command(["new", "--help"])

            # Step 3: Conclude CLI section
            narrator.step("Project scaffolded with zero external dependencies")
            artifacts = narrator.finish()

            if os.environ.get("RECORD_DEMO") == "1":
                assert "vtt" in artifacts and artifacts["vtt"].exists()
                assert "webm" in artifacts and artifacts["webm"].exists()
        finally:
            os.chdir(orig_cwd)


TODO_APP_FACTORY = """
import uvicorn
from todo_app.entrypoints.ch01_in_memory import build_app
app = build_app()
uvicorn.run(app, host="127.0.0.1", port={port})
"""


@pytest.mark.e2e
@pytest.mark.demo
def test_todo_ch01_browser_demo(page: Page, demo: DemoNarrator) -> None:
    """Record Chapter 1 interactive browser experience (OpenAPI Docs & Testing)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = f"examples/todo-app/src:{env.get('PYTHONPATH', '')}"

    with ephemeral_server(app_factory_code=TODO_APP_FACTORY, env=env) as server_url:
        demo.output_name = "todo-ch01-browser-demo"

        # 1. Open Swagger Docs
        docs_url = f"{server_url}/docs"
        demo.goto(
            docs_url, caption="Tutorial 1: Exploring automatic OpenAPI Swagger UI"
        )

        # 2. Verify endpoints
        post_endpoint = page.locator(".opblock-post").first
        expect(post_endpoint).to_be_visible()

        # 3. Expand POST /todos
        demo.click(
            post_endpoint, caption="Inspecting auto-generated POST /todos endpoint"
        )
        page.wait_for_timeout(800)

        # 4. Try it out
        try_it_out = page.get_by_text("Try it out").first
        if try_it_out.is_visible():
            demo.click(
                try_it_out, caption="Interacting live with CQRS CreateTodoCommand"
            )
            page.wait_for_timeout(800)

        # 5. Finish demo
        demo.step("Chapter 1 completed: In-memory CQRS To-Do Service verified!")
        page.wait_for_timeout(1200)
        demo.finish()
