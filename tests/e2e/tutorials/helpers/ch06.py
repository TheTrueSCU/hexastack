"""Chapter 6 step helpers: Production Observability & DevTools."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack_cli.testing.narrator import CliNarrator


def step_ch06_1_inspect_ui_command(
    narrator: CliNarrator, *, record: bool = True
) -> None:
    """Ch 6 - Step 1: Inspect DevTools interactive web UI launch options."""
    narrator.step(
        "Tutorial Chapter 6: Production Observability & Distributed Tracing",
        record=record,
    )
    narrator.run_command(["ui", "--help"], record=record)


def step_ch06_configure_observability(
    narrator: CliNarrator, *, record: bool = True
) -> None:
    """Ch 6 Orchestrator: Complete Chapter 6 setup."""
    step_ch06_1_inspect_ui_command(narrator, record=record)
