from hexastack_mcp.domain.metadata import (
    McpPromptMetadata,
    McpResourceMetadata,
    McpToolMetadata,
)


def test_mcp_metadata_models():
    tool_meta = McpToolMetadata(name="test_tool", description="Test description")
    assert tool_meta.name == "test_tool"
    assert tool_meta.description == "Test description"
    assert tool_meta.kind == "command"
    assert tool_meta.target is None

    # Custom kind and target
    custom_tool = McpToolMetadata(name="custom", kind="query", target=int)
    assert custom_tool.kind == "query"
    assert custom_tool.target is int

    res_meta = McpResourceMetadata(uri="hexastack://test", name="test_resource")
    assert res_meta.uri == "hexastack://test"
    assert res_meta.name == "test_resource"
    assert res_meta.description is None
    assert res_meta.mime_type == "application/json"
    assert res_meta.handler is None

    prompt_meta = McpPromptMetadata(name="test_prompt")
    assert prompt_meta.name == "test_prompt"
    assert prompt_meta.description is None
    assert prompt_meta.handler is None
