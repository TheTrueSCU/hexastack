"""Feature demo test recording the hexastack scaffolding CLI experience."""

import os
import tempfile
from pathlib import Path

import pytest
import typer

from hexastack.adapters.cli.scaffolding.commands import add_scaffold_commands
from hexastack_cli.testing.narrator import CliNarrator


@pytest.mark.demo
def test_scaffolding_cli_demo():
    """Record interactive CLI demonstration for hexastack new & init."""
    app = typer.Typer(name="hexastack")
    add_scaffold_commands(app)
    repo_root = Path.cwd()

    with tempfile.TemporaryDirectory() as tmpdir:
        orig_cwd = Path.cwd()
        try:
            os.chdir(tmpdir)
            narrator = CliNarrator(
                app,
                output_name="hexastack-scaffolding-cli-demo",
                output_dir=repo_root / "docs" / "assets" / "demos",
            )

            # Step 1: Display help menu
            narrator.step("Exploring Hexastack project scaffolding subcommands")
            res_help = narrator.run_command(["new", "--help"])
            assert res_help.exit_code == 0

            # Step 2: Scaffold a new web-api microservice
            narrator.step("Scaffolding a new REST Web API microservice with SQLite")
            res_new = narrator.run_command(
                ["new", "web-api", "billing-service", "--db", "sqlite"]
            )
            assert res_new.exit_code == 0
            assert Path(tmpdir, "billing-service", "pyproject.toml").exists()

            # Step 3: Scaffold an event-driven service
            narrator.step("Scaffolding an Event-Driven streaming service with Outbox")
            res_event = narrator.run_command(["new", "event-driven", "order-service"])
            assert res_event.exit_code == 0
            assert Path(tmpdir, "order-service", "pyproject.toml").exists()

            # Step 4: Finalize artifacts
            narrator.step(
                "Microservices successfully scaffolded with full hexagonal architecture"
            )
            artifacts = narrator.finish()

            if os.environ.get("RECORD_DEMO") == "1":
                assert "vtt" in artifacts and artifacts["vtt"].exists()
                assert "webm" in artifacts and artifacts["webm"].exists()
        finally:
            os.chdir(orig_cwd)
