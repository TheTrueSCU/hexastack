"""Unit tests for CliNarrator test recording engine."""

import os
import tempfile
from pathlib import Path
from typing import Any

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


def test_cli_narrator_custom_bin_name():
    """Verify CliNarrator formats commands with custom bin_name."""
    app = typer.Typer(name="custom_tool")

    @app.command()
    def ping():
        typer.echo("pong")

    narrator = CliNarrator(app, bin_name="custom-cli")
    res_bin = narrator.bin_name
    assert res_bin == "custom-cli"

    narrator_auto = CliNarrator(app)
    res_auto = narrator_auto.bin_name
    assert res_auto == "custom_tool"


def test_cli_narrator_checkpoint_segment_fast_mode():
    """Verify checkpoint_segment resets event buffers while preserving application state."""
    app = typer.Typer()
    state = {"count": 0}

    @app.command()
    def increment():
        state["count"] += 1
        typer.echo(f"Count is now {state['count']}")

    narrator = CliNarrator(app, output_name="multi-stage-fast")

    # Stage 1
    narrator.step("Stage 1: Initial increment")
    res1 = narrator.run_command([])
    exit1 = res1.exit_code
    out1 = res1.output
    assert exit1 == 0
    assert "Count is now 1" in out1

    seg1_artifacts = narrator.checkpoint_segment("stage1")
    assert seg1_artifacts == {}

    # Stage 2: Continues with existing application state
    narrator.step("Stage 2: Second increment")
    res2 = narrator.run_command([])
    exit2 = res2.exit_code
    out2 = res2.output
    assert exit2 == 0
    assert "Count is now 2" in out2

    seg2_artifacts = narrator.checkpoint_segment("stage2")
    assert seg2_artifacts == {}

    final_artifacts = narrator.finish()
    assert final_artifacts == {}


def test_cli_narrator_checkpoint_segment_recording_mode(monkeypatch):
    """Verify checkpoint_segment generates segmented artifacts with normalized timestamps."""
    app = typer.Typer()

    @app.command()
    def step_cmd(label: str):
        typer.echo(f"Executed: {label}")

    rendered_calls: list[dict[str, Any]] = []

    def mock_render_video(
        events: Any, output_path: Any, title: Any, **kwargs: Any
    ) -> tuple[Any, Any]:
        rendered_calls.append(
            {
                "events": events,
                "output_path": output_path,
                "title": title,
            }
        )
        vtt_path = output_path.with_suffix(".vtt")
        output_path.touch()
        vtt_path.touch()
        return output_path, vtt_path

    monkeypatch.setattr(
        "hexastack_cli.testing.terminal.render_cli_demo_video",
        mock_render_video,
    )
    monkeypatch.setenv("RECORD_DEMO", "1")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        narrator = CliNarrator(app, output_name="tutorial-demo", output_dir=out_dir)

        # Stage 1
        narrator.step("Stage 1: Setup")
        res1 = narrator.run_command(["part1"])
        exit1 = res1.exit_code
        assert exit1 == 0
        seg1 = narrator.checkpoint_segment("part1-setup")

        has_webm1 = "webm" in seg1 and seg1["webm"].exists()
        has_vtt1 = "vtt" in seg1 and seg1["vtt"].exists()
        assert has_webm1 is True
        assert has_vtt1 is True
        assert seg1["webm"].name == "tutorial-demo-part1-setup.webm"

        # Verify Stage 1 event timestamps start at 0.0s
        first_call = rendered_calls[0]
        events1 = first_call["events"]
        events1_len = len(events1)
        assert events1_len > 0
        first_ts1 = events1[0].timestamp
        assert first_ts1 == 0.0

        # Stage 2
        narrator.step("Stage 2: Execution")
        res2 = narrator.run_command(["part2"])
        exit2 = res2.exit_code
        assert exit2 == 0
        seg2 = narrator.checkpoint_segment("part2-exec")

        has_webm2 = "webm" in seg2 and seg2["webm"].exists()
        assert has_webm2 is True
        assert seg2["webm"].name == "tutorial-demo-part2-exec.webm"

        # Verify Stage 2 event timestamps are normalized to 0.0s
        second_call = rendered_calls[1]
        events2 = second_call["events"]
        events2_len = len(events2)
        assert events2_len > 0
        first_ts2 = events2[0].timestamp
        assert first_ts2 == 0.0

        # Finish consolidates all segment artifacts
        final = narrator.finish()
        has_seg1_key = "tutorial-demo-part1-setup_webm" in final
        has_seg2_key = "tutorial-demo-part2-exec_webm" in final
        assert has_seg1_key is True
        assert has_seg2_key is True


def test_cli_narrator_finish_auto_checkpoints_final_segment(monkeypatch):
    """Verify finish() auto-checkpoints remaining events as 'final' and consolidates all segments."""
    app = typer.Typer()

    @app.command()
    def step1():
        print("Executing Step 1")

    @app.command()
    def step2():
        print("Executing Step 2")

    rendered_calls = []

    def mock_render_video(events, output_path, title):
        output_path.write_text("dummy-video-data")
        vtt_file = output_path.with_suffix(".vtt")
        vtt_file.write_text("WEBVTT\n")
        rendered_calls.append({"events": events, "output_path": output_path})
        return output_path, vtt_file

    monkeypatch.setattr(
        "hexastack_cli.testing.terminal.render_cli_demo_video",
        mock_render_video,
    )
    monkeypatch.setenv("RECORD_DEMO", "1")

    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        narrator = CliNarrator(app, output_name="auto-final-demo", output_dir=out_dir)

        # Segment 1
        narrator.step("Phase 1")
        res1 = narrator.run_command(["step1"])
        exit1 = res1.exit_code
        assert exit1 == 0
        seg1 = narrator.checkpoint_segment("phase1")
        has_seg1 = "webm" in seg1 and seg1["webm"].exists()
        assert has_seg1 is True

        # Phase 2 without manual checkpoint
        narrator.step("Phase 2")
        res2 = narrator.run_command(["step2"])
        exit2 = res2.exit_code
        assert exit2 == 0

        # finish() should auto-checkpoint phase 2 as 'final' and return all consolidated artifacts
        final = narrator.finish()
        has_phase1_key = "auto-final-demo-phase1_webm" in final
        has_final_key = "auto-final-demo-final_webm" in final
        has_latest_webm = "webm" in final and final["webm"].exists()
        assert has_phase1_key is True
        assert has_final_key is True
        assert has_latest_webm is True
