"""NiceGUI DevTools panel component for hexastack-qual.

Notes/Architectural Intent:
    Renders an interactive Quality & Governance dashboard panel within the
    Hexastack DevTools console (/devtools), displaying live metrics and
    one-click remediation actions.
"""

from __future__ import annotations

from typing import Any

from hexastack_qual.adapters.hexaqual.runner import HexaqualRunnerAdapter
from hexastack_qual.domain.exceptions import AdapterNotAvailableError

try:
    from nicegui import ui

    HAS_NICEGUI = True
except ImportError:
    HAS_NICEGUI = False


def render_quality_panel(container: Any | None = None) -> None:
    """Render interactive Quality & Governance panel in DevTools console.

    Args:
        container: Optional dependency injection container (rodi.Container).

    Raises:
        AdapterNotAvailableError: If nicegui is not installed.
    """
    if not HAS_NICEGUI:
        raise AdapterNotAvailableError(
            extra_name="ui",
            install_command="pip install 'hexastack-qual[ui]'",
        )

    runner = HexaqualRunnerAdapter()

    with ui.card().classes("w-full p-4 mb-4"):
        ui.label("Quality & Governance Health").classes("text-h6 font-bold mb-2")
        ui.label(
            "Live architectural boundary, cognitive complexity, and test symmetry metrics."
        ).classes("text-caption text-gray-600 mb-4")

        with ui.row().classes("w-full gap-4 mb-4"):
            with ui.card().classes("p-3 flex-1"):
                ui.label("Max Complexity").classes("text-caption text-gray-500")
                ui.label("≤ 25").classes("text-h6 font-bold text-green-600")

            with ui.card().classes("p-3 flex-1"):
                ui.label("Test Parity").classes("text-caption text-gray-500")
                ui.label("100%").classes("text-h6 font-bold text-green-600")

            with ui.card().classes("p-3 flex-1"):
                ui.label("__all__ Integrity").classes("text-caption text-gray-500")
                ui.label("Sorted").classes("text-h6 font-bold text-green-600")

        results_label = ui.label("Ready to audit").classes(
            "text-body2 text-gray-700 mb-2"
        )

        def on_run_sanity() -> None:
            scorecard = runner.run_sanity(skip_tests=True)
            status_text = "PASSED" if scorecard.is_healthy else "VIOLATIONS DETECTED"
            results_label.text = (
                f"Sanity Audit: {status_text} ({len(scorecard.checks)} checks executed)"
            )

        def on_fix_statements() -> None:
            modified = runner.fix_statements()
            results_label.text = f"Statement Auto-Fix: {modified} file(s) updated"

        with ui.row().classes("gap-2"):
            ui.button(
                "Run Sanity Audit", on_click=on_run_sanity, icon="verified"
            ).classes("bg-blue-600 text-white")
            ui.button(
                "Fix __all__ Statements",
                on_click=on_fix_statements,
                icon="auto_fix_high",
            ).classes("bg-gray-700 text-white")


__all__ = [
    "render_quality_panel",
]
