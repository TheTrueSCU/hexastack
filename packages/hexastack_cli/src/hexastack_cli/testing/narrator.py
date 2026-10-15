"""Feature demo narrator and Playwright terminal video recorder for CLI commands."""

from __future__ import annotations

import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from typer.testing import CliRunner, Result

from hexastack_cli.testing.events import TerminalEvent
from hexastack_core.utils.fs import atomic_write_text


class CliNarrator:
    """Orchestrates structured narrative CLI execution, step recording, and video rendering.

    Notes/Architectural Intent:
        1. In standard CI/unit test mode, runs instantly with zero delay via in-memory CliRunner.
        2. In demo recording mode (`RECORD_DEMO=1`), captures keystrokes, output tokens, and narrative steps,
           and directly renders a fixed-window, auto-scrolling .webm video via Playwright.
    """

    def __init__(
        self,
        app: Any,
        output_name: str | None = None,
        output_dir: Path | None = None,
        width: int = 100,
        height: int = 24,
        bin_name: str | None = None,
    ) -> None:
        """Initialize CLI narrator attached to a Typer or Click application.

        Args:
            app: Target Typer application instance.
            output_name: Base filename (without extension) for saving recordings.
            output_dir: Target output directory for generated demo artifacts.
            width: Terminal column width.
            height: Terminal row height.
            bin_name: Display binary name for recorded command lines (defaults to app name or 'hexastack').

        Notes/Architectural Intent:
            Configurable bin_name allows narrating commands from across the hexa- family of tools
            (e.g., hexaflow, hexaqual, hq) with accurate terminal prompts in generated demo videos.
        """
        self.app = app
        self.output_name = output_name
        self.output_dir = output_dir or Path("docs/assets/demos")
        self.width = width
        self.height = height
        app_name = getattr(getattr(app, "info", None), "name", None)
        self.bin_name = bin_name or app_name or "hexastack"
        self.record_mode = os.environ.get("RECORD_DEMO") in ("1", "true", "True")
        self.runner = CliRunner()
        self.start_time: float = time.time()
        self.events: list[TerminalEvent] = []
        self.captions: list[tuple[float, float, str]] = []
        self._current_step_start: float | None = None
        self._current_step_text: str | None = None
        self._segment_count: int = 0
        self.segments: dict[str, dict[str, Path]] = {}

    def step(self, title: str, *, record: bool = True) -> None:
        """Mark a new narrative step in the CLI demo recording.

        Args:
            title: Human-readable narrative explanation shown in subtitle banner.
            record: Whether to emit the step subtitle and recording marker (defaults to True).
        """
        if not record:
            return

        now = time.time() - self.start_time
        if self._current_step_start is not None and self._current_step_text is not None:
            self.captions.append(
                (self._current_step_start, now, self._current_step_text)
            )

        self._current_step_start = now
        self._current_step_text = title

        if self.record_mode:
            self.events.append(
                TerminalEvent(event_type="step", payload=title, timestamp=now)
            )

    def run_command(
        self,
        args: list[str],
        env: dict[str, str] | None = None,
        input: str | None = None,
        record: bool = True,
    ) -> Result:
        """Execute a CLI command within the active Typer application.

        Args:
            args: Command-line argument strings.
            env: Optional environment variables.
            input: Optional stdin input string.
            record: Whether to record this command invocation and output (defaults to True).

        Returns:
            CliRunner Result containing exit code, stdout, and stderr.
        """
        cmd_str = f"{self.bin_name} {' '.join(args)}"

        if self.record_mode and record:
            # 1. Record input command string
            now = time.time() - self.start_time
            self.events.append(
                TerminalEvent(
                    event_type="input",
                    payload=f"$ {cmd_str}\n",
                    timestamp=now,
                )
            )

        # Execute command in-memory
        # If an event loop is running in the active thread, offload execution to a thread pool
        # to ensure commands invoking asyncio.run() (e.g. Hexaflow simulate/run) succeed without RuntimeError.
        try:
            asyncio.get_running_loop()
            is_loop_running = True
        except RuntimeError:
            is_loop_running = False

        if is_loop_running:
            with ThreadPoolExecutor(max_workers=1) as pool:
                res = pool.submit(
                    self.runner.invoke, self.app, args, input=input, env=env
                ).result()
        else:
            res = self.runner.invoke(self.app, args, input=input, env=env)

        if self.record_mode and record:
            # 2. Record command output text
            now = time.time() - self.start_time
            output_text = res.stdout if res.stdout else ""
            if output_text:
                self.events.append(
                    TerminalEvent(
                        event_type="output",
                        payload=output_text,
                        timestamp=now,
                    )
                )

        return res

    def checkpoint_segment(self, name: str | None = None) -> dict[str, Path]:
        """Flush the current recording segment to video and subtitle artifacts.

        Slices recorded terminal events and narration captions since the last checkpoint,
        renders the segment video (.webm) and WebVTT subtitle track (.vtt), and resets
        the segment event buffer while preserving the underlying execution state
        (Typer application context, filesystem, and databases).

        Args:
            name: Suffix or name for this segment (e.g. 'part1-scaffolding'). If omitted,
                defaults to 'segment-<N>'.

        Returns:
            Dictionary containing paths to generated segment artifacts ('webm', 'vtt').

        Notes/Architectural Intent:
            Enables dogfooding multi-step tutorials (e.g. Hexaflow stages) to produce digestible
            micro-demo videos per stage without incurring the overhead of running separate,
            disconnected test harnesses.
        """
        self._segment_count += 1
        if name:
            segment_name = (
                f"{self.output_name}-{name}"
                if self.output_name and not name.startswith(f"{self.output_name}-")
                else name
            )
        else:
            base = self.output_name or "cli-demo"
            segment_name = f"{base}-segment-{self._segment_count}"

        if not self.record_mode:
            self.events = []
            self.captions = []
            self.start_time = time.time()
            self._current_step_start = None
            self._current_step_text = None
            return {}

        now = time.time() - self.start_time
        if self._current_step_start is not None and self._current_step_text is not None:
            self.captions.append(
                (self._current_step_start, now, self._current_step_text)
            )

        out_dir = self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        artifacts: dict[str, Path] = {}

        # 1. Normalize segment event timestamps so the segment video begins at 0.0s
        if self.events:
            base_ts = self.events[0].timestamp
            segment_events = [
                TerminalEvent(
                    event_type=e.event_type,
                    payload=e.payload,
                    timestamp=max(0.0, e.timestamp - base_ts),
                )
                for e in self.events
            ]
        else:
            segment_events = []

        # 2. Render segment video and true-timing VTT via Playwright Rich Terminal
        from hexastack_cli.testing.terminal import render_cli_demo_video

        video_path = out_dir / f"{segment_name}.webm"
        video_file, vtt_file = render_cli_demo_video(
            events=segment_events,
            output_path=video_path,
            title=f"{self.bin_name} CLI — {segment_name}",
        )
        artifacts["webm"] = video_file
        artifacts["vtt"] = vtt_file
        self.segments[segment_name] = artifacts

        # 3. Reset segment event buffer and start time for the next segment
        self.events = []
        self.captions = []
        self.start_time = time.time()
        self._current_step_start = None
        self._current_step_text = None

        return artifacts

    def finish(self) -> dict[str, Path]:
        """Finalize the recording and render video and caption artifacts.

        Returns:
            Dictionary containing paths to generated artifact files (e.g. 'webm', 'vtt').
        """
        if not self.record_mode:
            return {}

        if self.events:
            if self._segment_count > 0:
                self.checkpoint_segment("final")
                all_artifacts: dict[str, Path] = {}
                for seg_name, arts in self.segments.items():
                    for k, v in arts.items():
                        all_artifacts[f"{seg_name}_{k}"] = v
                if self.segments:
                    latest_seg = list(self.segments.values())[-1]
                    all_artifacts.update(latest_seg)
                return all_artifacts

            now = time.time() - self.start_time
            if (
                self._current_step_start is not None
                and self._current_step_text is not None
            ):
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
            atomic_write_text(vtt_path, "\n".join(vtt_lines), encoding="utf-8")
            artifacts["vtt"] = vtt_path

            # 2. Render directly to .webm video via Playwright Rich Terminal
            from hexastack_cli.testing.terminal import render_cli_demo_video

            video_path = out_dir / f"{base_name}.webm"
            render_cli_demo_video(
                events=self.events,
                output_path=video_path,
                title=f"{self.bin_name} CLI — {base_name}",
            )
            artifacts["webm"] = video_path

            return artifacts

        all_artifacts: dict[str, Path] = {}
        for seg_name, arts in self.segments.items():
            for k, v in arts.items():
                all_artifacts[f"{seg_name}_{k}"] = v
        if self.segments:
            latest_seg = list(self.segments.values())[-1]
            all_artifacts.update(latest_seg)
        return all_artifacts

    @staticmethod
    def _format_vtt_time(seconds: float) -> str:
        """Format seconds float into standard WebVTT timestamp (HH:MM:SS.mmm)."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"


__all__ = [
    "CliNarrator",
    "TerminalEvent",
]
