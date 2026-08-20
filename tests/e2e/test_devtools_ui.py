"""Playwright End-to-End browser tests and feature demo recording for Hexastack DevTools."""

import pytest
from playwright.sync_api import Page, expect

from hexastack_fastapi.testing.cursor import smart_click
from hexastack_fastapi.testing.recorder import DemoNarrator


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
    smart_click(page, page.get_by_text("Feature Flags"))
    expect(page.get_by_text("Active Feature Flags")).to_be_visible()

    # 5. Click DI Container tab
    smart_click(page, page.get_by_text("DI Container"))
    expect(page.get_by_text("Dependency Injection Services")).to_be_visible()


@pytest.mark.e2e
@pytest.mark.demo
def test_devtools_interactive_ping_dispatcher(
    devtools_server: str, page: Page, demo: DemoNarrator
) -> None:
    """Narrated feature demo: Inspect CQRS pipeline & live dispatch PingDemoCommand."""
    demo.goto(devtools_server, caption="Welcome to Hexastack Interactive DevTools")

    # Step 1: Switch to CQRS Registry tab
    demo.click(
        page.get_by_text("CQRS Registry"),
        caption="Navigating to the CQRS Registry & Pipeline visualizer",
    )

    # Step 2: Locate and dispatch the ping demo command
    dispatch_button = page.get_by_role("button", name="Dispatch Ping Command")
    expect(dispatch_button).to_be_visible()

    demo.click(
        dispatch_button,
        caption="Dispatching PingDemoCommand through the middleware pipeline",
    )

    # Step 3: Verify execution result logged in DOM
    demo.step("Observing live handler response and execution logs")
    expect(page.get_by_text("➡️ [DISPATCH] PingDemoCommand")).to_be_visible(timeout=5000)
    expect(page.get_by_text("✅ [SUCCESS] Result: reply='PONG:")).to_be_visible(
        timeout=5000
    )
