"""Terminal session testing and feature demo narration engine for CLI applications."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from typer.testing import CliRunner


@dataclass
class TerminalEvent:
    """Represents a discrete timestamped event in a recorded terminal session."""

    time_offset: float
    event_type: str  # "input", "output", "step"
    payload: str


class CliNarrator:
    """Orchestrates CLI command execution, human-like typing emulation, and session recording.

    Notes/Architectural Intent:
        Provides a unified interface for testing CLI tools that:
        1. In standard test / CI mode: Runs instantly via in-memory CliRunner.
        2. In demo mode (RECORD_DEMO=1): Generates WebVTT narration subtitles
           and directly renders a fixed-window, auto-scrolling .webm video via Playwright.
    """

    def __init__(
        self,
        app: Any,
        output_name: str | None = None,
        output_dir: Path | None = None,
        width: int = 100,
        height: int = 24,
    ) -> None:
        """Initialize CLI narrator attached to a Typer or Click application.

        Args:
            app: Target Typer application instance.
            output_name: Base filename (without extension) for saving recordings.
            output_dir: Target output directory for generated demo artifacts.
            width: Terminal column width.
            height: Terminal row height.
        """
        self.app = app
        self.output_name = output_name
        self.output_dir = output_dir or Path("docs/assets/demos")
        self.width = width
        self.height = height
        self.record_mode = os.environ.get("RECORD_DEMO") in ("1", "true", "True")
        self.runner = CliRunner()
        self.start_time: float = time.time()
        self.events: list[TerminalEvent] = []
        self.captions: list[tuple[float, float, str]] = []
        self._current_step_start: float | None = None
        self._current_step_text: str | None = None

    def step(self, caption: str) -> None:
        """Add a descriptive chapter step / subtitle narration for viewers.

        Args:
            caption: Subtitle narration text explaining the current terminal action.
        """
        now = time.time() - self.start_time

        if self._current_step_start is not None and self._current_step_text is not None:
            self.captions.append(
                (self._current_step_start, now, self._current_step_text)
            )

        self._current_step_start = now
        self._current_step_text = caption
        self.events.append(
            TerminalEvent(time_offset=now, event_type="step", payload=caption)
        )

    def run_command(
        self,
        args: list[str],
        caption: str | None = None,
        input_text: str | None = None,
        type_delay: float = 0.05,
    ) -> Any:
        """Execute a CLI command with simulated typing cadence and output recording.

        Args:
            args: Command line arguments list (e.g. ["new", "web-api", "my-service"]).
            caption: Optional narration step explaining this command.
            input_text: Optional interactive stdin text to feed to the command.
            type_delay: Seconds per keystroke when recording in demo mode.

        Returns:
            CliRunner invocation result.
        """
        if caption:
            self.step(caption)

        cmd_str = "hexastack " + " ".join(args)
        cmd_start = time.time() - self.start_time

        if self.record_mode:
            # Simulate human keystroke cadence in event timeline
            sim_time = cmd_start
            for char in f"$ {cmd_str}\n":
                sim_time += type_delay
                self.events.append(
                    TerminalEvent(
                        time_offset=sim_time, event_type="input", payload=char
                    )
                )

        # Execute command synchronously
        result = self.runner.invoke(self.app, args, input=input_text)
        out_time = time.time() - self.start_time

        self.events.append(
            TerminalEvent(
                time_offset=out_time, event_type="output", payload=result.output
            )
        )

        return result

    def finish(self) -> dict[str, Path]:
        """Finalize recording and export .webm and .vtt subtitle artifacts.

        Returns:
            Dictionary containing written artifact paths.
        """
        if not self.record_mode:
            return {}

        now = time.time() - self.start_time
        if self._current_step_start is not None and self._current_step_text is not None:
            self.captions.append(
                (self._current_step_start, now, self._current_step_text)
            )

        out_dir = self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        base_name = self.output_name or "cli-demo"
        artifacts: dict[str, Path] = {}

        # 1. Export WebVTT (.vtt) synchronized narration subtitles
        vtt_lines = ["WEBVTT", ""]
        for idx, (start_s, end_s, text) in enumerate(self.captions, start=1):
            vtt_lines.append(str(idx))
            vtt_lines.append(
                f"{self._format_vtt_time(start_s)} --> {self._format_vtt_time(end_s)}"
            )
            vtt_lines.append(text)
            vtt_lines.append("")

        vtt_path = out_dir / f"{base_name}.vtt"
        vtt_path.write_text("\n".join(vtt_lines), encoding="utf-8")
        artifacts["vtt"] = vtt_path

        # 2. Render directly to .webm video via Playwright Rich Terminal
        try:
            from hexastack_cli.testing.terminal import render_cli_demo_video

            video_path = out_dir / f"{base_name}.webm"
            render_cli_demo_video(
                events=self.events,
                output_path=video_path,
                title=f"Hexastack CLI — {base_name}",
            )
            artifacts["webm"] = video_path
        except Exception:
            pass

        return artifacts

    @staticmethod
    def _format_vtt_time(seconds: float) -> str:
        """Format seconds into WebVTT timestamp (HH:MM:SS.mmm)."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"


__all__ = [
    "CliNarrator",
    "TerminalEvent",
]
