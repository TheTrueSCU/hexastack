"""Chapter 1 step helpers: Pure Domain, REST & CLI Scaffolding."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack_cli.testing.narrator import CliNarrator


def step_ch01_1_scaffold_project(narrator: CliNarrator, *, record: bool = True) -> None:
    """Ch 1 - Step 1: Scaffold To-Do microservice with in-memory persistence."""
    narrator.step(
        "Tutorial Chapter 1: Scaffolding a To-Do REST microservice", record=record
    )
    res = narrator.run_command(
        ["new", "web-api", "todo-app", "--db", "in-memory"],
        record=record,
    )
    if res.exit_code != 0:
        raise RuntimeError(
            f"Ch 1 Step 1 failed with exit code {res.exit_code}: {res.output}"
        )


def step_ch01_2_inspect_layout(narrator: CliNarrator, *, record: bool = True) -> None:
    """Ch 1 - Step 2: Inspect pure hexagonal architecture CLI layout and help."""
    narrator.step("Inspecting pure hexagonal architecture layout", record=record)
    narrator.run_command(["new", "--help"], record=record)


def step_ch01_scaffold_minimal(narrator: CliNarrator, *, record: bool = True) -> None:
    """Ch 1 Orchestrator: Complete Chapter 1 setup."""
    step_ch01_1_scaffold_project(narrator, record=record)
    step_ch01_2_inspect_layout(narrator, record=record)
