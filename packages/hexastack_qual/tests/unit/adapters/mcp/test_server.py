"""Unit tests for MCP server builder and runner.

Notes/Architectural Intent:
    Validates create_quality_mcp_server and run_quality_mcp_server configuration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hexastack_qual.adapters.mcp.server import (
    create_quality_mcp_server,
    run_quality_mcp_server,
)


def test_create_quality_mcp_server() -> None:
    """Ensure create_quality_mcp_server builds a server instance."""
    server = create_quality_mcp_server(server_name="test-server")
    assert server is not None
    assert getattr(server, "name", "") == "test-server"


@pytest.mark.asyncio
async def test_run_quality_mcp_server() -> None:
    """Ensure run_quality_mcp_server delegates to run_stdio_async."""
    with (
        patch(
            "hexastack_qual.adapters.mcp.server.create_quality_mcp_server",
            return_value=MagicMock(),
        ),
        patch(
            "hexastack_qual.adapters.mcp.server.run_stdio_async",
            new_callable=AsyncMock,
        ) as mock_stdio,
    ):
        await run_quality_mcp_server()
        assert mock_stdio.call_count == 1
