from hexastack_core.domain.exceptions import HexastackError
from hexastack_mcp.domain.exceptions import (
    McpError,
    ResourceNotFoundError,
    ToolExecutionError,
)


def test_mcp_exceptions():
    err = ToolExecutionError("Failed to execute tool")
    assert isinstance(err, McpError)
    assert isinstance(err, HexastackError)
    assert str(err) == "Failed to execute tool"

    res_err = ResourceNotFoundError("Resource not found")
    assert isinstance(res_err, McpError)
