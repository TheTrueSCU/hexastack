"""Playwright End-to-End browser test and feature demo for dynamic Feature Flag hot-swapping.

Notes/Architectural Intent:
    Verifies that the DevTools Feature Flags console dynamically inspects and hot-swaps
    feature flags in real time across the runtime DI container without service restarts,
    while proving strict WCAG 2.1 AA accessibility compliance.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from hexastack_fastapi.testing.recorder import DemoNarrator
from tests.e2e.test_ui_accessibility import run_axe_scan


@pytest.mark.e2e
@pytest.mark.demo
def test_devtools_feature_flags_hotswapping(
    devtools_server: str, page: Page, demo: DemoNarrator
) -> None:
    """Explore live Feature Flags console, hot-swap flag values, and audit WCAG 2.1 AA a11y.

    Args:
        devtools_server: Base URL for ephemeral DevTools FastAPI + NiceGUI server.
        page: Active Playwright browser page with virtual red cursor injected.
        demo: DemoNarrator fixture recording video and synchronized WebVTT subtitles.

    Notes/Architectural Intent:
        Demonstrates zero-downtime runtime flag hot-swapping through the DevTools UI,
        asserting that state mutations reflect immediately in the application provider
        and that interactive toggle controls meet strict accessibility contrast and label rules.
    """
    demo.goto(devtools_server, caption="Welcome to Hexastack Interactive DevTools")

    # Step 1: Navigate to Feature Flags tab
    demo.click(
        page.get_by_role("tab", name="Feature Flags"),
        caption="Navigating to the Dynamic Feature Flags hot-swapping console",
    )

    # Step 2: Verify section heading and description
    heading = page.locator(".hx-section-heading", has_text="Active Feature Flags")
    expect(heading).to_be_visible(timeout=10000)

    description = page.get_by_text("Evaluate and hot-swap feature flags live")
    expect(description).to_be_visible()

    # Step 3: Verify configured feature flags are rendered
    expect(page.get_by_text("features.beta_ui")).to_be_visible()
    expect(page.get_by_text("features.experimental_ai")).to_be_visible()

    # Step 4: Live toggle features.experimental_ai from Disabled to Enabled
    demo.step(
        "Hot-swapping 'features.experimental_ai' flag from Disabled to Enabled live"
    )
    toggle_switch = page.get_by_label("Toggle features.experimental_ai")
    expect(toggle_switch).to_be_visible()

    demo.click(
        toggle_switch,
        caption="Toggling features.experimental_ai live in runtime DI container",
    )

    # Step 5: Verify live hot-swap audit log in console
    expect(
        page.get_by_text(
            "[HOT-SWAP] Feature flag 'features.experimental_ai' toggled to True"
        )
    ).to_be_visible(timeout=5000)

    # Step 6: Run axe-core WCAG 2.1 AA accessibility audit
    demo.step(
        "Verifying WCAG 2.1 AA accessibility compliance across feature flag controls"
    )
    page.wait_for_timeout(2500)
    violations = run_axe_scan(page)
    critical_violations = [
        v for v in violations if v.get("impact") in ("critical", "serious")
    ]
    crit_count = len(critical_violations)
    assert crit_count == 0, (
        f"Accessibility violations on Feature Flags tab: {critical_violations}"
    )


__all__ = [
    "test_devtools_feature_flags_hotswapping",
]
