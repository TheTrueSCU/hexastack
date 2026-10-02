"""Chapter 4 step helpers: Events, Outbox & Notifications."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack_cli.testing.narrator import CliNarrator


def step_ch04_1_inspect_outbox_relay(
    narrator: CliNarrator, *, record: bool = True
) -> None:
    """Ch 4 - Step 1: Inspect Transactional Outbox background relay daemon commands."""
    narrator.step(
        "Tutorial Chapter 4: Event-Driven Architecture with Outbox & CloudEvents",
        record=record,
    )
    narrator.run_command(["outbox", "--help"], record=record)


def step_ch04_configure_events_outbox(
    narrator: CliNarrator, *, record: bool = True
) -> None:
    """Ch 4 Orchestrator: Complete Chapter 4 setup."""
    step_ch04_1_inspect_outbox_relay(narrator, record=record)
