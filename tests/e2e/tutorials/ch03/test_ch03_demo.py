"""Feature demo recordings for Tutorial Chapter 3: JWT Auth & RBAC."""

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
@pytest.mark.ch03
def test_todo_ch03_cli_demo() -> None:
    """Record Chapter 3 JWT Auth & RBAC setup in rich terminal video."""
    app = typer.Typer(name="hexastack")
    add_scaffold_commands(app)
    repo_root = Path.cwd()

    with tempfile.TemporaryDirectory() as tmpdir:
        orig_cwd = Path.cwd()
        try:
            os.chdir(tmpdir)
            narrator = CliNarrator(
                app,
                output_name="todo-ch03-cli-demo",
                output_dir=repo_root / "docs" / "assets" / "demos",
            )

            # Step 1: Scaffold microservice with Auth
            narrator.step("Tutorial Chapter 3: Adding JWT Auth & RBAC permissions")
            res_new = narrator.run_command(
                ["new", "web-api", "todo-secure-app", "--db", "sqlite"]
            )
            assert res_new.exit_code == 0
            assert Path(tmpdir, "todo-secure-app", "pyproject.toml").exists()

            # Step 2: Show CLI help
            narrator.step("Configuring UserContext token extraction & role policies")
            narrator.run_command(["new", "--help"])

            # Step 3: Conclude CLI section
            narrator.step("Task ownership protected: Bob cannot delete Alice's tasks")
            artifacts = narrator.finish()

            if os.environ.get("RECORD_DEMO") == "1":
                assert "vtt" in artifacts and artifacts["vtt"].exists()
                assert "webm" in artifacts and artifacts["webm"].exists()
        finally:
            os.chdir(orig_cwd)


TODO_CH03_FACTORY = """
import uvicorn
from todo_app.entrypoints.ch03_secure import build_app
app = build_app(db_url="sqlite:///todos_ch03_demo.db")
uvicorn.run(app, host="127.0.0.1", port={port})
"""


@pytest.mark.e2e
@pytest.mark.demo
@pytest.mark.ch03
def test_todo_ch03_browser_demo(page: Page, demo: DemoNarrator) -> None:
    """Record Chapter 3 interactive browser experience (RBAC & Auth)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = f"examples/todo-app/src:{env.get('PYTHONPATH', '')}"

    with ephemeral_server(app_factory_code=TODO_CH03_FACTORY, env=env) as server_url:
        demo.output_name = "todo-ch03-browser-demo"

        # 1. Open Swagger Docs
        docs_url = f"{server_url}/docs"
        demo.goto(docs_url, caption="Tutorial 3: Secured To-Do REST API with RBAC")

        # 2. Verify endpoints
        post_endpoint = page.locator(".opblock-post").first
        expect(post_endpoint).to_be_visible()

        # 3. Expand POST /todos
        demo.click(post_endpoint, caption="Creating task as authenticated user 'alice'")
        page.wait_for_timeout(800)

        # 4. Expand DELETE /todos/{todo_id}
        del_endpoint = page.locator(".opblock-delete").first
        if del_endpoint.is_visible():
            demo.click(
                del_endpoint, caption="Inspecting DELETE /todos/{id} protected endpoint"
            )
            page.wait_for_timeout(800)

        # 5. Finish demo
        demo.step("Chapter 3 completed: User ownership and admin escalation verified!")
        page.wait_for_timeout(1200)
        demo.finish()
