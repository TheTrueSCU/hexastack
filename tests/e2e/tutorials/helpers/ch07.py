"""Chapter 7 step helpers: High-Performance gRPC & Dual Transport Parity."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack_cli.testing.narrator import CliNarrator


def step_ch07_1_list_grpc_services(
    narrator: CliNarrator, *, record: bool = True
) -> None:
    """Ch 7 - Step 1: Introspect registered gRPC servicers and Protobuf schemas."""
    narrator.step(
        "Tutorial Chapter 7: High-Performance gRPC & Dual Transport Parity",
        record=record,
    )
    narrator.run_command(["grpc", "list"], record=record)


def step_ch07_2_inspect_grpc_compile(
    narrator: CliNarrator, *, record: bool = True
) -> None:
    """Ch 7 - Step 2: Inspect in-process Protobuf compilation options."""
    narrator.step("Inspecting in-process Protobuf compiler tooling", record=record)
    narrator.run_command(["grpc", "compile", "--help"], record=record)


def step_ch07_configure_grpc(narrator: CliNarrator, *, record: bool = True) -> None:
    """Ch 7 Orchestrator: Complete Chapter 7 setup."""
    step_ch07_1_list_grpc_services(narrator, record=record)
    step_ch07_2_inspect_grpc_compile(narrator, record=record)
