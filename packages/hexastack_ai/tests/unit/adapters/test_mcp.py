from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp.client.session import ClientSession
from mcp.types import CallToolResult, TextContent, Tool
from pydantic_ai import Agent

from hexastack_ai.adapters.mcp import (
    attach_external_mcp_tools,
    create_mcp_client_tool,
)


@pytest.mark.anyio
async def test_create_mcp_client_tool_schema_and_invocation():
    """Verify tool parameter derivation and session.call_tool execution."""
    mock_session = MagicMock(spec=ClientSession)
    mock_session.call_tool = AsyncMock(
        return_value=CallToolResult(
            content=[TextContent(type="text", text="processed query: 42")]
        )
    )

    tool_def = Tool(
        name="test_tool",
        description="A test tool definition",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
                "active": {"type": "boolean"},
            },
            "required": ["query"],
        },
    )

    tool_fn = create_mcp_client_tool(mock_session, tool_def)

    # Check function metadata
    assert getattr(tool_fn, "__name__", None) == "test_tool"
    assert getattr(tool_fn, "__doc__", None) == "A test tool definition"

    sig = getattr(tool_fn, "__signature__", None)
    assert sig is not None
    param_names = list(sig.parameters.keys())
    assert "query" in param_names
    assert "limit" in param_names
    assert "active" in param_names

    # Required param has empty default
    assert sig.parameters["query"].annotation is str
    # Optional params have None default
    assert sig.parameters["limit"].annotation is int
    assert sig.parameters["limit"].default is None

    # Execute tool
    res = await tool_fn(query="SELECT 1", limit=10, active=True)
    assert res == "processed query: 42"

    call_args = mock_session.call_tool.call_args
    assert call_args[0][0] == "test_tool"
    assert call_args[1]["arguments"] == {
        "query": "SELECT 1",
        "limit": 10,
        "active": True,
    }


@pytest.mark.anyio
async def test_create_mcp_client_tool_multiple_content():
    """Verify multiple TextContent items are joined with newline."""
    mock_session = MagicMock(spec=ClientSession)
    mock_session.call_tool = AsyncMock(
        return_value=CallToolResult(
            content=[
                TextContent(type="text", text="Line 1"),
                TextContent(type="text", text="Line 2"),
            ]
        )
    )

    tool_def = Tool(
        name="multi_line_tool",
        description="Returns multiple text lines",
        inputSchema={"type": "object", "properties": {}},
    )

    tool_fn = create_mcp_client_tool(mock_session, tool_def)
    res = await tool_fn()
    assert res == "Line 1\nLine 2"


@pytest.mark.anyio
async def test_attach_external_mcp_tools():
    """Verify listing tools from session and registering them on PydanticAI Agent."""
    mock_session = MagicMock(spec=ClientSession)
    mock_session.list_tools = AsyncMock(
        return_value=MagicMock(
            tools=[
                Tool(
                    name="tool_alpha",
                    description="Alpha tool",
                    inputSchema={
                        "type": "object",
                        "properties": {"arg_a": {"type": "string"}},
                    },
                ),
                Tool(
                    name="tool_beta",
                    description="Beta tool",
                    inputSchema={
                        "type": "object",
                        "properties": {"arg_b": {"type": "number"}},
                    },
                ),
            ]
        )
    )
    mock_session.call_tool = AsyncMock(
        return_value=CallToolResult(
            content=[TextContent(type="text", text="beta result")]
        )
    )

    agent = Agent("test")
    registered = await attach_external_mcp_tools(agent, mock_session)

    assert "tool_alpha" in registered
    assert "tool_beta" in registered
    assert len(registered) == 2

    # Execute agent run with test model
    res = await agent.run("Run tool beta")
    res_output = getattr(res, "output", None)
    assert res_output is not None
