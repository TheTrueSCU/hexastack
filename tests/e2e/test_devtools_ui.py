import socket
import subprocess
import sys
import time
from collections.abc import Generator

import pytest
from playwright.sync_api import Page, expect


def _get_free_port() -> int:
    """Find a dynamically available free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def devtools_server() -> Generator[str]:
    """Spawn ephemeral background Hexastack FastAPI + NiceGUI server on random open port."""
    port = _get_free_port()
    server_url = f"http://127.0.0.1:{port}/_devtools"

    cmd = [
        sys.executable,
        "-c",
        f"""
import uvicorn
from hexastack.adapters.fastapi import create_demo_app

app = create_demo_app()
uvicorn.run(app, host="127.0.0.1", port={port}, log_level="warning")
""",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    import urllib.error
    import urllib.request

    ready = False
    for _ in range(40):
        try:
            with urllib.request.urlopen(server_url, timeout=1) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.25)

    if not ready:
        proc.kill()
        raise RuntimeError(f"DevTools server failed to start at {server_url}")

    yield server_url

    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.mark.e2e
def test_devtools_page_rendering_and_tabs(devtools_server: str, page: Page) -> None:
    """Verify DevTools header, tabs, and CQRS pipeline render properly in real browser."""
    page.goto(devtools_server)

    # 1. Check DevTools header
    expect(page.get_by_text("Hexastack DevTools")).to_be_visible()

    # 2. Check tab headers exist
    expect(page.get_by_text("CQRS Registry")).to_be_visible()
    expect(page.get_by_text("Feature Flags")).to_be_visible()
    expect(page.get_by_text("DI Container")).to_be_visible()

    # 3. Check middleware pipeline visualizer chips
    expect(page.get_by_text("CorrelationMiddleware")).to_be_visible()
    expect(page.get_by_text("TimingMiddleware")).to_be_visible()
    expect(page.get_by_text("LoggingMiddleware")).to_be_visible()
    expect(page.get_by_text("Handler Execution")).to_be_visible()

    # 4. Click Feature Flags tab
    page.get_by_text("Feature Flags").click()
    expect(page.get_by_text("Active Feature Flags")).to_be_visible()

    # 5. Click DI Container tab
    page.get_by_text("DI Container").click()
    expect(page.get_by_text("Dependency Injection Services")).to_be_visible()


@pytest.mark.e2e
def test_devtools_interactive_ping_dispatcher(devtools_server: str, page: Page) -> None:
    """Verify live command execution runner dispatches PingDemoCommand and shows log."""
    page.goto(devtools_server)

    # Switch to CQRS Registry tab if not default
    page.get_by_text("CQRS Registry").click()

    # Locate and click Dispatch Ping Command button
    dispatch_button = page.get_by_role("button", name="Dispatch Ping Command")
    expect(dispatch_button).to_be_visible()
    dispatch_button.click()

    # Verify execution result logged in DOM
    expect(page.get_by_text("➡️ [DISPATCH] PingDemoCommand")).to_be_visible(timeout=5000)
    expect(page.get_by_text("✅ [SUCCESS] Result: reply='PONG:")).to_be_visible(
        timeout=5000
    )
