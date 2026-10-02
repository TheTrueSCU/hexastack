"""Chapter 3 step helpers: JWT Authentication & RBAC."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack_cli.testing.narrator import CliNarrator


def step_ch03_1_inspect_registry_auth(
    narrator: CliNarrator, *, record: bool = True
) -> None:
    """Ch 3 - Step 1: Introspect authenticated CQRS command and query topology."""
    narrator.step(
        "Tutorial Chapter 3: Role-Based Access Control (RBAC) & JWT Auth", record=record
    )
    narrator.run_command(["inspect", "registry"], record=record)


def step_ch03_configure_jwt_auth(narrator: CliNarrator, *, record: bool = True) -> None:
    """Ch 3 Orchestrator: Complete Chapter 3 setup."""
    step_ch03_1_inspect_registry_auth(narrator, record=record)
