"""Unit tests for MCP tools, resources, and prompts.

Notes/Architectural Intent:
    Validates tool function execution, resource serialization, prompt templates,
    and registration with McpServerRegistry.
"""

from __future__ import annotations

import json
from unittest.mock import patch

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
from hexastack_qual.domain.models import (
    MutantReport,
    PrHealthSummary,
    QualityScorecard,
)

from hexastack_mcp.infra.registries.server import McpServerRegistry


def test_tool_run_sanity_check() -> None:
    """Ensure tool_run_sanity_check returns serializable dictionary."""
    mock_scorecard = QualityScorecard(target="core", is_healthy=True)
    with patch(
        "hexastack_qual.adapters.mcp.tools._runner.run_sanity",
        return_value=mock_scorecard,
    ):
        res = tool_run_sanity_check("core", skip_tests=True)
        assert res["target"] == "core"
        assert res["is_healthy"] is True


def test_tool_format_statements() -> None:
    """Ensure tool_format_statements returns status and count."""
    with patch(
        "hexastack_qual.adapters.mcp.tools._runner.fix_statements",
        return_value=3,
    ):
        res = tool_format_statements("ai")
        assert res["status"] == "success"
        assert res["modified_files_count"] == 3


def test_tool_inspect_surviving_mutants() -> None:
    """Ensure tool_inspect_surviving_mutants returns report dictionary."""
    mock_report = MutantReport(package_name="db", mutation_score=100.0)
    with patch(
        "hexastack_qual.adapters.mcp.tools._runner.inspect_surviving_mutants",
        return_value=mock_report,
    ):
        res = tool_inspect_surviving_mutants("db")
        assert res["package_name"] == "db"
        assert res["mutation_score"] == 100.0


def test_tool_query_impacted_tests() -> None:
    """Ensure tool_query_impacted_tests returns list of package names."""
    with patch(
        "hexastack_qual.adapters.mcp.tools._runner.get_test_impact",
        return_value=["core", "cqrs"],
    ):
        res = tool_query_impacted_tests("HEAD~1")
        assert res == ["core", "cqrs"]


def test_tool_get_pr_health() -> None:
    """Ensure tool_get_pr_health returns PR summary dictionary."""
    mock_pr = PrHealthSummary(
        pr_number=55,
        title="feat: test",
        state="open",
        ci_status="success",
    )
    with patch(
        "hexastack_qual.adapters.mcp.tools._runner.get_pr_health",
        return_value=mock_pr,
    ):
        res = tool_get_pr_health(55)
        assert res["pr_number"] == 55
        assert res["ci_status"] == "success"


def test_resource_workspace_scorecard() -> None:
    """Ensure resource_workspace_scorecard produces valid JSON."""
    mock_scorecard = QualityScorecard(target="workspace", is_healthy=True)
    with patch(
        "hexastack_qual.adapters.mcp.tools._runner.run_sanity",
        return_value=mock_scorecard,
    ):
        raw = resource_workspace_scorecard()
        data = json.loads(raw)
        assert data["target"] == "workspace"
        assert data["is_healthy"] is True


def test_prompt_triage_mutants() -> None:
    """Ensure prompt_triage_mutants includes instructions and package name."""
    prompt = prompt_triage_mutants("flow")
    assert "package 'flow'" in prompt
    assert "inspect_surviving_mutants" in prompt


def test_register_quality_mcp_tools() -> None:
    """Ensure register_quality_mcp_tools populates McpServerRegistry."""
    registry = McpServerRegistry()
    res_reg = register_quality_mcp_tools(registry)
    tool_names = [t.name for t in res_reg.tools]
    assert "run_sanity_check" in tool_names
    assert "format_statements" in tool_names
    assert "inspect_surviving_mutants" in tool_names
    assert "query_impacted_tests" in tool_names
    assert "get_pr_health" in tool_names
    assert len(res_reg.resources) >= 1
    assert len(res_reg.prompts) >= 1


def test_get_quality_tools() -> None:
    """Ensure get_quality_tools returns all 5 tool functions."""
    tools = get_quality_tools()
    assert len(tools) == 5
    assert tool_run_sanity_check in tools
