"""Unit tests for MCP stdio adapter."""

from hexastack_mcp.adapters.stdio import run_stdio_async, run_stdio_server


def test_mcp_stdio_helpers_callable() -> None:
    assert callable(run_stdio_async)
    assert callable(run_stdio_server)
