"""Chapter 5 step helpers: AI Assistant & MCP Tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack_cli.testing.narrator import CliNarrator


def step_ch05_1_list_mcp_tools(narrator: CliNarrator, *, record: bool = True) -> None:
    """Ch 5 - Step 1: Introspect registered MCP AI tools, prompts, and resources."""
    narrator.step(
        "Tutorial Chapter 5: Model Context Protocol (MCP) AI Tools", record=record
    )
    narrator.run_command(["mcp", "list"], record=record)


def step_ch05_2_generate_mcp_config(
    narrator: CliNarrator, *, record: bool = True
) -> None:
    """Ch 5 - Step 2: Generate client MCP JSON config for AI IDEs."""
    narrator.step(
        "Generating MCP configuration for Gemini and Antigravity IDE", record=record
    )
    narrator.run_command(["mcp", "config", "--client", "antigravity"], record=record)


def step_ch05_configure_ai_mcp(narrator: CliNarrator, *, record: bool = True) -> None:
    """Ch 5 Orchestrator: Complete Chapter 5 setup."""
    step_ch05_1_list_mcp_tools(narrator, record=record)
    step_ch05_2_generate_mcp_config(narrator, record=record)
