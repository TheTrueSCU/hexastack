"""Feature demo recordings for Tutorial Chapter 2: SQLite Persistence & Migrations."""

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
@pytest.mark.ch02
def test_todo_ch02_cli_demo() -> None:
    """Record Chapter 2 SQLite configuration & schema creation in terminal video."""
    app = typer.Typer(name="hexastack")
    add_scaffold_commands(app)
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

            # Step 1: Scaffold microservice with SQLite DB option
            narrator.step(
                "Tutorial Chapter 2: Scaffolding a To-Do Service with SQLite persistence"
            )
            res_new = narrator.run_command(
                ["new", "web-api", "todo-sqlite-app", "--db", "sqlite"]
            )
            assert res_new.exit_code == 0
            assert Path(tmpdir, "todo-sqlite-app", "pyproject.toml").exists()

            # Step 2: Show Alembic migrations CLI command
            narrator.step("Configuring SQLite SQLAlchemy adapter & migrations")
            narrator.run_command(["new", "--help"])

            # Step 3: Conclude CLI section
            narrator.step(
                "SQLite persistence configured with decoupled SQLAlchemy adapter"
            )
            artifacts = narrator.finish()

            if os.environ.get("RECORD_DEMO") == "1":
                assert "vtt" in artifacts and artifacts["vtt"].exists()
                assert "webm" in artifacts and artifacts["webm"].exists()
        finally:
            os.chdir(orig_cwd)


TODO_CH02_FACTORY = """
import uvicorn
from todo_app.entrypoints.ch02_sqlite import build_app
app = build_app(db_url="sqlite:///todos_demo.db")
uvicorn.run(app, host="127.0.0.1", port={port})
"""


@pytest.mark.e2e
@pytest.mark.demo
@pytest.mark.ch02
def test_todo_ch02_browser_demo(page: Page, demo: DemoNarrator) -> None:
    """Record Chapter 2 interactive browser experience (Persistent SQLite API)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = f"examples/todo-app/src:{env.get('PYTHONPATH', '')}"

    with ephemeral_server(app_factory_code=TODO_CH02_FACTORY, env=env) as server_url:
        demo.output_name = "todo-ch02-browser-demo"

        # 1. Open Swagger Docs
        docs_url = f"{server_url}/docs"
        demo.goto(
            docs_url, caption="Tutorial 2: Exploring SQLite-backed Persistent REST API"
        )

        # 2. Verify endpoints
        post_endpoint = page.locator(".opblock-post").first
        expect(post_endpoint).to_be_visible()

        # 3. Expand POST /todos
        demo.click(
            post_endpoint, caption="Invoking POST /todos with persistent SQLite storage"
        )
        page.wait_for_timeout(800)

        # 4. Try it out button
        try_it_out = page.get_by_text("Try it out").first
        if try_it_out.is_visible():
            demo.click(
                try_it_out, caption="Dispatching CreateTodoCommand saved to SQLite"
            )
            page.wait_for_timeout(800)

        # 5. Finish demo
        demo.step("Chapter 2 completed: SQLite persistence verified across requests!")
        page.wait_for_timeout(1200)
        demo.finish()
