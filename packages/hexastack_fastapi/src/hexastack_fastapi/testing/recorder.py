"""Feature demo narrator and WebVTT caption generator for Playwright recordings."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_fastapi.testing.cursor import VIRTUAL_CURSOR_SCRIPT

CAPTION_BANNER_SCRIPT = """
(() => {
    const initBanner = () => {
        if (document.getElementById('hexastack-caption-banner')) return;
        const banner = document.createElement('div');
        banner.id = 'hexastack-caption-banner';
        banner.style.position = 'fixed';
        banner.style.bottom = '32px';
        banner.style.left = '50%';
        banner.style.transform = 'translateX(-50%)';
        banner.style.backgroundColor = 'rgba(15, 23, 42, 0.92)';
        banner.style.color = '#ffffff';
        banner.style.padding = '12px 24px';
        banner.style.borderRadius = '8px';
        banner.style.fontSize = '17px';
        banner.style.fontFamily = 'system-ui, -apple-system, sans-serif';
        banner.style.fontWeight = '500';
        banner.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.5)';
        banner.style.border = '1px solid rgba(255, 255, 255, 0.15)';
        banner.style.backdropFilter = 'blur(8px)';
        banner.style.zIndex = '2147483646';
        banner.style.display = 'none';
        banner.style.transition = 'opacity 0.2s ease-in-out';
        banner.style.pointerEvents = 'none';
        banner.style.maxWidth = '80%';
        banner.style.textAlign = 'center';

        const root = document.documentElement || document.body;
        if (root) root.appendChild(banner);
    };

    window.addEventListener('DOMContentLoaded', initBanner);
    setInterval(() => {
        const root = document.documentElement || document.body;
        if (root) initBanner();
    }, 100);
})();
"""


class DemoNarrator:
    """Orchestrates synchronized UI actions, live banner captions, and WebVTT subtitle export.

    Notes/Architectural Intent:
        Provides high-level narrative actions (`step`, `click`, `fill`, `goto`) that:
        1. Run at full native speed with zero overhead during CI / standard test runs.
        2. In demo recording mode (`RECORD_DEMO=1`), displays an elegant on-screen DOM subtitle
           banner burned into the video, animates smooth cursor movement, and writes .vtt subtitle files.
    """

    def __init__(self, page: Any, output_name: str | None = None) -> None:
        """Initialize demo narrator attached to a Playwright page.

        Args:
            page: Active Playwright Page instance.
            output_name: Base filename (without extension) for saving .vtt captions.

        Raises:
            MissingDependencyError: If `playwright` is not installed.
        """
        try:
            import playwright  # noqa: F401
        except ImportError as e:
            raise MissingDependencyError(
                "Playwright is required to record feature demos. "
                "Install with 'pip install hexastack-fastapi[testing]' or 'pip install playwright'."
            ) from e

        self.page = page
        self.output_name = output_name
        self.record_mode = os.environ.get("RECORD_DEMO") in ("1", "true", "True")
        self.start_time: float = time.time()
        self.captions: list[tuple[float, float, str]] = []
        self._current_step_start: float | None = None
        self._current_step_text: str | None = None

        if self.record_mode:
            self.page.add_init_script(VIRTUAL_CURSOR_SCRIPT)
            self.page.add_init_script(CAPTION_BANNER_SCRIPT)

    def step(self, caption: str) -> None:
        """Mark a new narrative step with human-readable on-screen caption banner.

        Args:
            caption: Subtitle narrative explaining the current action to viewers.
        """
        now = time.time() - self.start_time

        if self._current_step_start is not None and self._current_step_text is not None:
            self.captions.append(
                (self._current_step_start, now, self._current_step_text)
            )

        self._current_step_start = now
        self._current_step_text = caption

        if not self.record_mode:
            return

        safe_caption = caption.replace("'", "\\'").replace("\n", " ")
        self.page.evaluate(
            f"""(() => {{
                const banner = document.getElementById('hexastack-caption-banner');
                if (banner) {{
                    banner.innerText = '{safe_caption}';
                    banner.style.display = 'block';
                    banner.style.opacity = '1';
                }}
            }})();"""
        )
        self.page.wait_for_timeout(400)

    def goto(self, url: str, caption: str | None = None) -> None:
        """Navigate to a URL with optional step caption."""
        if caption:
            self.step(caption)
        self.page.goto(url)
        if self.record_mode:
            self.page.wait_for_timeout(600)
            if caption:
                self.step(caption)

    def click(self, locator: Any, caption: str | None = None, steps: int = 35) -> None:
        """Smoothly click a target element with visual cursor interpolation and caption.

        Args:
            locator: Playwright Locator or element target.
            caption: Optional narration text for this specific click.
            steps: Number of mouse interpolation steps for smooth movement.
        """
        if caption:
            self.step(caption)

        element = locator.first if hasattr(locator, "first") else locator

        if not self.record_mode:
            element.click()
            return

        element.scroll_into_view_if_needed()
        box = element.bounding_box()
        if not box:
            element.click()
            return

        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2

        self.page.mouse.move(x, y, steps=steps)
        self.page.wait_for_timeout(800)

        self.page.mouse.down()
        page_timeout = 300
        self.page.wait_for_timeout(page_timeout)
        self.page.mouse.up()
        self.page.wait_for_timeout(700)

    def fill(self, locator: Any, value: str, caption: str | None = None) -> None:
        """Type text into an input field with optional human-like typing cadence.

        Args:
            locator: Playwright input locator.
            value: Text to fill.
            caption: Optional narration text.
        """
        if caption:
            self.step(caption)

        element = locator.first if hasattr(locator, "first") else locator

        if not self.record_mode:
            element.fill(value)
            return

        self.click(element)
        element.fill("")
        for char in value:
            self.page.keyboard.type(char, delay=60)
        self.page.wait_for_timeout(400)

    def finish(self) -> Path | None:
        """Complete the demo recording and write WebVTT subtitles to disk.

        Returns:
            Path to the written .vtt file if in demo mode, or None if in CI mode.
        """
        if not self.record_mode:
            return None

        now = time.time() - self.start_time
        if self._current_step_start is not None and self._current_step_text is not None:
            self.captions.append(
                (self._current_step_start, now, self._current_step_text)
            )

        self.page.wait_for_timeout(1000)

        # Generate WebVTT content
        vtt_lines = ["WEBVTT", ""]
        for idx, (start_s, end_s, text) in enumerate(self.captions, start=1):
            vtt_lines.append(str(idx))
            vtt_lines.append(
                f"{self._format_vtt_time(start_s)} --> {self._format_vtt_time(end_s)}"
            )
            vtt_lines.append(text)
            vtt_lines.append("")

        out_dir = Path("docs/assets/demos")
        out_dir.mkdir(parents=True, exist_ok=True)
        vtt_path = out_dir / f"{self.output_name or 'demo'}.vtt"
        vtt_path.write_text("\n".join(vtt_lines), encoding="utf-8")
        return vtt_path

    @staticmethod
    def _format_vtt_time(seconds: float) -> str:
        """Format seconds float into standard WebVTT timestamp (HH:MM:SS.mmm)."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"


__all__ = [
    "DemoNarrator",
]
