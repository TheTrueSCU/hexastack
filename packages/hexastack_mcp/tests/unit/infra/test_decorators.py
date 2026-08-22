"""Unit tests for MCP decorators."""

from hexastack_mcp.infra.decorators import mcp_tool


def test_mcp_tool_decorator_callable() -> None:
    assert callable(mcp_tool)
