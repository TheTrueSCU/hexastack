"""Feature demo recordings for Tutorial Chapter 4: Outbox & Event Notifications."""

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
@pytest.mark.ch04
def test_todo_ch04_cli_demo() -> None:
    """Record Chapter 4 Event-Driven Outbox & Notification setup in terminal video."""
    app = typer.Typer(name="hexastack")
    add_scaffold_commands(app)
    repo_root = Path.cwd()

    with tempfile.TemporaryDirectory() as tmpdir:
        orig_cwd = Path.cwd()
        try:
            os.chdir(tmpdir)
            narrator = CliNarrator(
                app,
                output_name="todo-ch04-cli-demo",
                output_dir=repo_root / "docs" / "assets" / "demos",
            )

            # Step 1: Scaffold event-driven microservice
            narrator.step("Tutorial Chapter 4: Event-Driven Outbox & CloudEvents")
            res_new = narrator.run_command(
                ["new", "event-driven", "todo-events-service"]
            )
            assert res_new.exit_code == 0
            assert Path(tmpdir, "todo-events-service", "pyproject.toml").exists()

            # Step 2: Show CLI help
            narrator.step(
                "Configuring NotificationPort: Stdout, File, or Apprise (ntfy/Discord)"
            )
            narrator.run_command(["new", "--help"])

            # Step 3: Conclude CLI section
            narrator.step(
                "Admin override triggers automatic audit notice and push alerts"
            )
            artifacts = narrator.finish()

            if os.environ.get("RECORD_DEMO") == "1":
                assert "vtt" in artifacts and artifacts["vtt"].exists()
                assert "webm" in artifacts and artifacts["webm"].exists()
        finally:
            os.chdir(orig_cwd)


TODO_CH04_FACTORY = """
import uvicorn
from todo_app.entrypoints.ch04_event_driven import build_app
app = build_app(db_url="sqlite:///todos_ch04_demo.db")
uvicorn.run(app, host="127.0.0.1", port={port})
"""


@pytest.mark.e2e
@pytest.mark.demo
@pytest.mark.ch04
def test_todo_ch04_browser_demo(page: Page, demo: DemoNarrator) -> None:
    """Record Chapter 4 interactive browser experience (Event notifications)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = f"examples/todo-app/src:{env.get('PYTHONPATH', '')}"

    with ephemeral_server(app_factory_code=TODO_CH04_FACTORY, env=env) as server_url:
        demo.output_name = "todo-ch04-browser-demo"

        # 1. Open Swagger Docs
        docs_url = f"{server_url}/docs"
        demo.goto(docs_url, caption="Tutorial 4: Event-Driven To-Do REST API")

        # 2. Verify endpoints
        post_endpoint = page.locator(".opblock-post").first
        expect(post_endpoint).to_be_visible()

        # 3. Expand POST /todos
        demo.click(post_endpoint, caption="Alice creates task 'Deploy to Production'")
        page.wait_for_timeout(800)

        # 4. Expand DELETE /todos/{todo_id}
        del_endpoint = page.locator(".opblock-delete").first
        if del_endpoint.is_visible():
            demo.click(
                del_endpoint,
                caption="Admin deletes task -> Triggers NotificationPort alert",
            )
            page.wait_for_timeout(800)

        # 5. Finish demo
        demo.step("Chapter 4 completed: Outbox events & push notifications dispatched!")
        page.wait_for_timeout(1200)
        demo.finish()
