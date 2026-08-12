from hexastack_core.domain.exceptions import HexastackError
from hexastack_mcp.domain.exceptions import (
    McpError,
    ResourceNotFoundError,
    ToolExecutionError,
)
from hexastack_mcp.domain.metadata import (
    McpPromptMetadata,
    McpResourceMetadata,
    McpToolMetadata,
)


def test_mcp_exceptions():
    err = ToolExecutionError("Failed to execute tool")
    assert isinstance(err, McpError)
    assert isinstance(err, HexastackError)
    assert str(err) == "Failed to execute tool"

    res_err = ResourceNotFoundError("Resource not found")
    assert isinstance(res_err, McpError)


def test_mcp_metadata_models():
    tool_meta = McpToolMetadata(name="test_tool", description="Test description")
    assert tool_meta.name == "test_tool"
    assert tool_meta.kind == "command"

    res_meta = McpResourceMetadata(uri="hexastack://test", name="test_resource")
    assert res_meta.uri == "hexastack://test"
    assert res_meta.mime_type == "application/json"

    prompt_meta = McpPromptMetadata(name="test_prompt")
    assert prompt_meta.name == "test_prompt"
