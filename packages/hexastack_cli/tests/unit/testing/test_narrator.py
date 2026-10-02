"""Unit tests for CliNarrator test recording engine."""

import os
import tempfile
from pathlib import Path

import typer

from hexastack_cli.testing.narrator import CliNarrator


def test_cli_narrator_fast_execution():
    """Verify CliNarrator executes commands quickly in standard testing mode."""
    app = typer.Typer()

    @app.command()
    def greet(name: str = "World"):
        typer.echo(f"Hello, {name}!")

    narrator = CliNarrator(app, output_name="test-greet")
    narrator.step("Greeting test step")
    result = narrator.run_command(["--name", "Alice"])

    assert result.exit_code == 0
    assert "Hello, Alice!" in result.output
    artifacts = narrator.finish()
    assert artifacts == {}


def test_cli_narrator_demo_recording_mode():
    """Verify CliNarrator exports .vtt subtitle file when RECORD_DEMO=1."""
    app = typer.Typer()

    @app.command()
    def build(target: str):
        typer.echo(f"Building target: {target}")

    orig_env = os.environ.get("RECORD_DEMO")
    os.environ["RECORD_DEMO"] = "1"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                narrator = CliNarrator(app, output_name="build-demo")
                narrator.step("Initiating production service build")
                result = narrator.run_command(["web-api"])

                assert result.exit_code == 0
                assert "Building target: web-api" in result.output

                artifacts = narrator.finish()
                assert "vtt" in artifacts and artifacts["vtt"].exists()

                # Verify WebVTT format
                vtt_text = artifacts["vtt"].read_text(encoding="utf-8")
                assert "WEBVTT" in vtt_text
                assert "Initiating production service build" in vtt_text
            finally:
                os.chdir(orig_cwd)
    finally:
        if orig_env is not None:
            os.environ["RECORD_DEMO"] = orig_env
        else:
            os.environ.pop("RECORD_DEMO", None)
