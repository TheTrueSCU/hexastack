"""Shared pytest fixtures for Playwright E2E and Feature Demo Recordings."""

import os
import re
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Browser, BrowserContext, Page

from hexastack_fastapi.testing.cursor import VIRTUAL_CURSOR_SCRIPT
from hexastack_fastapi.testing.recorder import DemoNarrator
from hexastack_fastapi.testing.server import EphemeralServer

DEMO_APP_CODE = """
import uvicorn
from hexastack.adapters.fastapi import create_demo_app

app = create_demo_app()
uvicorn.run(app, host="127.0.0.1", port={port}, log_level="warning")
"""


@pytest.fixture(scope="module")
def devtools_server() -> Generator[str]:
    """Spawn ephemeral background Hexastack FastAPI + NiceGUI server on random open port."""
    server = EphemeralServer(app_factory_code=DEMO_APP_CODE)
    url = server.start(ready_path="/_devtools")
    yield f"{url}/_devtools"
    server.stop()


@pytest.fixture
def demo_mode() -> bool:
    """Check if demo recording mode is active via RECORD_DEMO environment variable."""
    return os.environ.get("RECORD_DEMO", "0") in ("1", "true", "True")


def _sanitize_demo_name(node_name: str) -> str:
    """Derive clean, human-readable demo filename from pytest test node name."""
    clean = re.sub(r"\[.*?\]", "", node_name)
    if clean.startswith("test_"):
        clean = clean[5:]
    if clean.startswith("demo_"):
        clean = clean[5:]
    return clean.replace("_", "-").strip("-")


@pytest.fixture
def context(browser: Browser, demo_mode: bool) -> Generator[BrowserContext]:
    """Provide customized browser context with optional video recording in demo mode."""
    context_kwargs: dict[str, Any] = {
        "viewport": {"width": 1280, "height": 720},
    }

    if demo_mode:
        videos_dir = Path("docs/assets/demos")
        videos_dir.mkdir(parents=True, exist_ok=True)
        context_kwargs["record_video_dir"] = str(videos_dir)
        context_kwargs["record_video_size"] = {"width": 1280, "height": 720}

    ctx = browser.new_context(**context_kwargs)
    yield ctx
    ctx.close()


@pytest.fixture
def page(
    request: pytest.FixtureRequest, context: BrowserContext, demo_mode: bool
) -> Generator[Page]:
    """Provide Playwright Page with virtual red cursor injected in demo mode and clean video save."""
    pg = context.new_page()

    if demo_mode:
        pg.add_init_script(VIRTUAL_CURSOR_SCRIPT)

    video = pg.video

    yield pg

    clean_name = _sanitize_demo_name(request.node.name)
    pg.close()

    if demo_mode and video:
        target_video = Path(f"docs/assets/demos/{clean_name}.webm")
        video.save_as(str(target_video))
        video.delete()


@pytest.fixture
def demo(request: pytest.FixtureRequest, page: Page) -> Generator[DemoNarrator]:
    """Provide DemoNarrator fixture with matched, clean video and .vtt file renaming."""
    clean_name = _sanitize_demo_name(request.node.name)
    narrator = DemoNarrator(page, output_name=clean_name)
    yield narrator
    narrator.finish()
