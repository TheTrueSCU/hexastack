"""Model Context Protocol (MCP) tools, resources, and prompt definitions for hexastack-qual.

Notes/Architectural Intent:
    Exposes codebase audits, test parity verification, and mutant inspections
    directly to AI coding assistants via hexastack-mcp. Degrades gracefully if
    hexastack-mcp is not installed.
"""

from __future__ import annotations

import json
from typing import Any

from hexastack_qual.adapters.hexaqual.runner import HexaqualRunnerAdapter
from hexastack_qual.domain.exceptions import AdapterNotAvailableError

try:
    from hexastack_mcp.domain.metadata import (
        McpPromptMetadata,
        McpResourceMetadata,
        McpToolMetadata,
    )
    from hexastack_mcp.infra.registries.server import McpServerRegistry

    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    McpServerRegistry = Any  # type: ignore[misc,assignment]


_runner = HexaqualRunnerAdapter()


def _ensure_mcp() -> None:
    """Validate that hexastack-mcp extra is installed.

    Raises:
        AdapterNotAvailableError: If hexastack-mcp is not available.
    """
    if not HAS_MCP:
        raise AdapterNotAvailableError(
            extra_name="mcp",
            install_command="pip install 'hexastack-qual[mcp]'",
        )


def tool_run_sanity_check(
    package: str | None = None,
    skip_tests: bool = True,
) -> dict[str, Any]:
    """Execute quality sanity checks across target package or workspace.

    Args:
        package: Optional target package name (e.g. 'core', 'ai'). None for workspace.
        skip_tests: Whether to skip unit test suites for faster execution.

    Returns:
        JSON-serializable quality scorecard dictionary.
    """
    scorecard = _runner.run_sanity(package=package, skip_tests=skip_tests)
    return scorecard.model_dump()


def tool_format_statements(package: str | None = None) -> dict[str, Any]:
    """Auto-format and alphabetize __all__ export statements across modules.

    Args:
        package: Optional target package name. None for workspace.

    Returns:
        Dictionary reporting total modified files.
    """
    modified = _runner.fix_statements(package=package)
    return {"status": "success", "modified_files_count": modified}


def tool_inspect_surviving_mutants(
    package: str | None = None,
    actionable_only: bool = True,
) -> dict[str, Any]:
    """Inspect surviving code mutants and triage classifications.

    Args:
        package: Optional target package name.
        actionable_only: If True, filters only critical actionable mutants.

    Returns:
        Dictionary summarizing surviving mutants and triage details.
    """
    report = _runner.inspect_surviving_mutants(
        package=package,
        actionable_only=actionable_only,
    )
    return report.model_dump()


def tool_query_impacted_tests(base_ref: str = "origin/main") -> list[str]:
    """Compute test targets impacted by git diff changes relative to base_ref.

    Args:
        base_ref: Git reference or branch to compare against.

    Returns:
        List of impacted package names.
    """
    return _runner.get_test_impact(base_ref=base_ref)


def tool_get_pr_health(pr_number: int) -> dict[str, Any]:
    """Inspect GitHub Pull Request CI checks, CodeQL alerts, and review threads.

    Args:
        pr_number: GitHub pull request number.

    Returns:
        Dictionary summarizing PR health metrics.
    """
    summary = _runner.get_pr_health(pr_number=pr_number)
    return summary.model_dump()


def resource_workspace_scorecard() -> str:
    """Read live JSON quality scorecard for entire workspace."""
    scorecard = _runner.run_sanity(package=None, skip_tests=True)
    return json.dumps(scorecard.model_dump(), indent=2)


def prompt_triage_mutants(package: str) -> str:
    """Generate prompt template guiding the assistant to kill surviving mutants."""
    return (
        f"You are Fortifying Tests for package '{package}'.\n"
        f"1. Call inspect_surviving_mutants(package='{package}', actionable_only=True).\n"
        "2. Locate the mutated source line and understand why existing tests did not catch it.\n"
        "3. Write a new assertion or test case targeting the mutated condition.\n"
        "4. Run unit tests and verify the mutant is killed.\n"
    )


def register_quality_mcp_tools(registry: McpServerRegistry) -> McpServerRegistry:
    """Register quality tools, resources, and prompts onto an McpServerRegistry.

    Args:
        registry: Target McpServerRegistry instance.

    Returns:
        The configured registry.

    Raises:
        AdapterNotAvailableError: If hexastack-mcp is not installed.
    """
    _ensure_mcp()

    tools = [
        McpToolMetadata(
            name="run_sanity_check",
            description="Run fast workspace quality checks (Ruff, Ty, Complexity, Parity, __all__).",
            kind="function",
            target=tool_run_sanity_check,
            read_only=True,
        ),
        McpToolMetadata(
            name="format_statements",
            description="Auto-format and sort __all__ lists across modules.",
            kind="function",
            target=tool_format_statements,
            read_only=False,
        ),
        McpToolMetadata(
            name="inspect_surviving_mutants",
            description="Inspect surviving code mutants and triage classifications.",
            kind="function",
            target=tool_inspect_surviving_mutants,
            read_only=True,
        ),
        McpToolMetadata(
            name="query_impacted_tests",
            description="Compute test targets impacted by git diff changes.",
            kind="function",
            target=tool_query_impacted_tests,
            read_only=True,
        ),
        McpToolMetadata(
            name="get_pr_health",
            description="Inspect GitHub Pull Request CI checks and CodeQL findings.",
            kind="function",
            target=tool_get_pr_health,
            read_only=True,
        ),
    ]

    for tool in tools:
        registry.register_tool(tool)

    resource = McpResourceMetadata(
        uri="quality://workspace/scorecard",
        name="Workspace Quality Scorecard",
        description="Live architectural health and quality metrics for the workspace.",
        mime_type="application/json",
        handler=resource_workspace_scorecard,
    )
    registry.register_resource(resource)

    prompt = McpPromptMetadata(
        name="triage-mutants",
        description="Prompt template for triaging surviving mutants and writing tests.",
        handler=prompt_triage_mutants,
    )
    registry.register_prompt(prompt)

    return registry


def get_quality_tools() -> list[Any]:
    """Retrieve list of callable quality tool functions for in-process AI agents.

    Returns:
        List of tool functions suitable for agent attachment.
    """
    return [
        tool_run_sanity_check,
        tool_format_statements,
        tool_inspect_surviving_mutants,
        tool_query_impacted_tests,
        tool_get_pr_health,
    ]


__all__ = [
    "get_quality_tools",
    "prompt_triage_mutants",
    "register_quality_mcp_tools",
    "resource_workspace_scorecard",
    "tool_format_statements",
    "tool_get_pr_health",
    "tool_inspect_surviving_mutants",
    "tool_query_impacted_tests",
    "tool_run_sanity_check",
]
