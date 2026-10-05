"""Model Context Protocol (MCP) server and tool adapters for hexastack-qual.

Notes/Architectural Intent:
    Exports quality tools, resources, prompts, and server runners.
"""

from __future__ import annotations

from hexastack_qual.adapters.mcp.server import (
    create_quality_mcp_server,
    run_quality_mcp_server,
)
from hexastack_qual.adapters.mcp.tools import (
    get_quality_tools,
    prompt_triage_mutants,
    register_quality_mcp_tools,
    resource_workspace_scorecard,
    tool_format_statements,
    tool_get_pr_health,
    tool_inspect_surviving_mutants,
    tool_query_impacted_tests,
    tool_run_sanity_check,
)

__all__ = [
    "create_quality_mcp_server",
    "get_quality_tools",
    "prompt_triage_mutants",
    "register_quality_mcp_tools",
    "resource_workspace_scorecard",
    "run_quality_mcp_server",
    "tool_format_statements",
    "tool_get_pr_health",
    "tool_inspect_surviving_mutants",
    "tool_query_impacted_tests",
    "tool_run_sanity_check",
]
