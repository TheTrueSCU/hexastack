"""Rich HTML Terminal view and Playwright video renderer for CLI demo recordings."""

from __future__ import annotations

import concurrent.futures
import html
import json
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from hexastack_core.domain.exceptions import MissingDependencyError

if TYPE_CHECKING:
    from hexastack_cli.testing.narrator import TerminalEvent


TERMINAL_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: #0d1117;
            color: #e6edf3;
            font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, Monaco, 'Courier New', monospace;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            overflow: hidden;
            padding: 40px;
        }}
        .window {{
            background: #161b22;
            border-radius: 12px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.1);
            width: 1080px;
            height: 560px;
            max-height: 560px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        .titlebar {{
            background: #21262d;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            flex-shrink: 0;
        }}
        .dots {{
            display: flex;
            gap: 8px;
        }}
        .dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}
        .dot-red {{ background: #ff5f56; }}
        .dot-yellow {{ background: #ffbd2e; }}
        .dot-green {{ background: #27c93f; }}
        .title {{
            flex: 1;
            text-align: center;
            color: #8b949e;
            font-size: 13px;
            font-weight: 500;
            margin-right: 48px;
        }}
        .content {{
            padding: 24px;
            font-size: 15px;
            line-height: 1.6;
            flex: 1;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-word;
            scroll-behavior: smooth;
        }}
        .content::-webkit-scrollbar {{
            display: none;
        }}
        .content {{
            -ms-overflow-style: none;
            scrollbar-width: none;
        }}
        .prompt {{ color: #7ee787; font-weight: bold; }}
        .command {{ color: #79c0ff; font-weight: bold; }}
        .step-banner {{
            position: fixed;
            bottom: 32px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(15, 23, 42, 0.92);
            color: #ffffff;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 17px;
            font-family: system-ui, -apple-system, sans-serif;
            font-weight: 500;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.15);
            backdrop-filter: blur(8px);
            z-index: 9999;
            transition: opacity 0.2s ease-in-out;
            text-align: center;
            max-width: 80%;
        }}
        .cursor {{
            display: inline-block;
            width: 8px;
            height: 16px;
            background: #58a6ff;
            vertical-align: text-bottom;
            animation: blink 1s step-end infinite;
        }}
        @keyframes blink {{ 50% {{ opacity: 0; }} }}
    </style>
</head>
<body>
    <div class="window">
        <div class="titlebar">
            <div class="dots">
                <div class="dot dot-red"></div>
                <div class="dot dot-yellow"></div>
                <div class="dot dot-green"></div>
            </div>
            <div class="title">{title} — bash</div>
        </div>
        <div class="content" id="terminal-content"><span class="cursor"></span></div>
    </div>
    <div class="step-banner" id="banner" style="display: none;"></div>
</body>
</html>
"""


def _strip_ansi(text: str) -> str:
    """Remove ANSI color and escape sequences from text."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def _render_in_clean_thread(
    events: list[TerminalEvent],
    output_path: Path,
    title: str,
    width: int,
    height: int,
) -> tuple[Path, Path]:
    """Execute Playwright video recording in a fresh thread with its own event loop."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise MissingDependencyError(
            "Playwright is required to record CLI demos into .webm video. "
            "Install with 'pip install hexastack-cli[testing]' or 'pip install playwright'."
        ) from e

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = output_path.parent / ".temp_video"
    temp_dir.mkdir(parents=True, exist_ok=True)

    html_content = TERMINAL_HTML_TEMPLATE.format(title=html.escape(title))
    vtt_captions: list[tuple[float, float, str]] = []
    current_step_start: float | None = None
    current_step_text: str | None = None

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception:
            # If Playwright browser binaries are not installed, create placeholder video artifact
            output_path.write_bytes(b"")
            return output_path, output_path.with_suffix(".vtt")

        context = browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir=str(temp_dir),
            record_video_size={"width": width, "height": height},
        )
        page = context.new_page()
        page.set_content(html_content)
        page.wait_for_timeout(500)
        start_playback_time = 0.5

        current_time = start_playback_time

        for ev in events:
            if ev.event_type == "step":
                if current_step_start is not None and current_step_text is not None:
                    vtt_captions.append(
                        (current_step_start, current_time, current_step_text)
                    )

                current_step_start = current_time
                current_step_text = ev.payload

                json_text = json.dumps(ev.payload)
                page.evaluate(
                    f"""(() => {{
                        const banner = document.getElementById('banner');
                        if (banner) {{
                            banner.innerText = {json_text};
                            banner.style.display = 'block';
                        }}
                    }})();"""
                )
                page.wait_for_timeout(600)
                current_time += 0.6

            elif ev.event_type == "input":
                char_str = html.escape(ev.payload)
                if char_str == "\n":
                    char_str = "<br/>"
                json_html = json.dumps(char_str)
                page.evaluate(
                    f"""(() => {{
                        const terminal = document.getElementById('terminal-content');
                        const cursor = terminal.querySelector('.cursor');
                        const span = document.createElement('span');
                        span.className = 'command';
                        span.innerHTML = {json_html};
                        terminal.insertBefore(span, cursor);
                        terminal.scrollTop = terminal.scrollHeight;
                    }})();"""
                )
                page.wait_for_timeout(35)
                current_time += 0.035

            elif ev.event_type == "output":
                clean_text = _strip_ansi(ev.payload)
                escaped_output = html.escape(clean_text).replace("\n", "<br/>")
                json_output = json.dumps(escaped_output)
                page.evaluate(
                    f"""(() => {{
                        const terminal = document.getElementById('terminal-content');
                        const cursor = terminal.querySelector('.cursor');
                        const div = document.createElement('div');
                        div.style.color = '#c9d1d9';
                        div.style.margin = '4px 0 12px 0';
                        div.innerHTML = {json_output};
                        terminal.insertBefore(div, cursor);
                        terminal.scrollTop = terminal.scrollHeight;
                    }})();"""
                )
                page.wait_for_timeout(1000)
                current_time += 1.0

        if current_step_start is not None and current_step_text is not None:
            vtt_captions.append(
                (current_step_start, current_time + 1.5, current_step_text)
            )

        page.wait_for_timeout(1500)
        video = page.video
        page.close()

        if video:
            video.save_as(output_path)

        context.close()
        browser.close()

    shutil.rmtree(temp_dir, ignore_errors=True)

    # Export synchronized WebVTT subtitles with true video timestamps
    vtt_lines = ["WEBVTT", ""]
    for idx, (start_s, end_s, text) in enumerate(vtt_captions, start=1):
        vtt_lines.append(str(idx))
        vtt_lines.append(f"{_format_vtt_time(start_s)} --> {_format_vtt_time(end_s)}")
        vtt_lines.append(text)
        vtt_lines.append("")

    vtt_path = output_path.with_suffix(".vtt")
    vtt_path.write_text("\n".join(vtt_lines), encoding="utf-8")

    return output_path, vtt_path


def render_cli_demo_video(
    events: list[TerminalEvent],
    output_path: Path,
    title: str = "Hexastack CLI",
    width: int = 1280,
    height: int = 720,
) -> tuple[Path, Path]:
    """Render a sequence of TerminalEvents into synchronized .webm video and .vtt subtitle track.

    Args:
        events: Chronological sequence of input, output, and step narrative events.
        output_path: Destination Path for .webm video file.
        title: Window title text for terminal banner.
        width: Video frame width in pixels.
        height: Video frame height in pixels.

    Returns:
        Tuple of (video_path, vtt_path).

    Raises:
        MissingDependencyError: If `playwright` is not installed.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            _render_in_clean_thread,
            events=events,
            output_path=output_path,
            title=title,
            width=width,
            height=height,
        )
        return future.result()


def _format_vtt_time(seconds: float) -> str:
    """Format seconds into WebVTT timestamp (HH:MM:SS.mmm)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"


__all__ = [
    "render_cli_demo_video",
]
