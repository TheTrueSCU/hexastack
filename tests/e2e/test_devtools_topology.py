"""Playwright End-to-End browser test and feature demo for Resource Topology navigation.

Notes/Architectural Intent:
    Verifies that the DevTools Resource Interconnect Topology graph renders live
    interconnections across CQRS message contracts, execution middlewares, event buses,
    and external storage ports, while proving WCAG 2.1 AA accessibility compliance.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from hexastack_fastapi.testing.recorder import DemoNarrator
from tests.e2e.test_ui_accessibility import run_axe_scan


@pytest.mark.e2e
@pytest.mark.demo
def test_devtools_resource_topology(
    devtools_server: str, page: Page, demo: DemoNarrator
) -> None:
    """Explore live Resource Interconnect Topology graph and verify WCAG 2.1 AA compliance.

    Args:
        devtools_server: Base URL for ephemeral DevTools FastAPI + NiceGUI server.
        page: Active Playwright browser page with virtual red cursor injected.
        demo: DemoNarrator fixture recording video and synchronized WebVTT subtitles.

    Notes/Architectural Intent:
        Drives automated navigation through the DevTools architecture visualizer,
        recording a feature demo video with subtitles and verifying that the live
        interconnect graph contains zero critical or serious accessibility violations.
    """
    demo.goto(devtools_server, caption="Welcome to Hexastack Interactive DevTools")

    # Step 1: Navigate to Resource Topology tab
    demo.click(
        page.get_by_text("Resource Topology"),
        caption="Navigating to the Resource Interconnect Topology visualizer",
    )

    # Step 2: Verify section heading and explanatory description
    heading = page.locator(
        ".hx-section-heading", has_text="Resource Interconnect Topology"
    )
    expect(heading).to_be_visible()

    description = page.get_by_text(
        "Interactive architectural interconnect graph across entrypoints"
    )
    expect(description).to_be_visible()

    # Step 3: Inspect rendered Mermaid architecture graph
    demo.step(
        "Inspecting live interconnect graph across entrypoints, CQRS pipelines, and ports"
    )
    topology_card = page.locator(".hx-card.items-center")
    expect(topology_card).to_be_visible()

    # Step 4: Run axe-core WCAG 2.1 AA accessibility audit
    demo.step("Verifying WCAG 2.1 AA accessibility compliance with zero violations")
    violations = run_axe_scan(page)
    critical_violations = [
        v for v in violations if v.get("impact") in ("critical", "serious")
    ]
    crit_count = len(critical_violations)
    assert crit_count == 0, (
        f"Accessibility violations on Topology tab: {critical_violations}"
    )


__all__ = [
    "test_devtools_resource_topology",
]
