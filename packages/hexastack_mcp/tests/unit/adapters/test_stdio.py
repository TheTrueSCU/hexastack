from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hexastack_mcp.adapters.stdio import run_stdio_async, run_stdio_server


def test_mcp_stdio_helpers_callable() -> None:
    assert callable(run_stdio_async)
    assert callable(run_stdio_server)


@pytest.mark.anyio
async def test_run_stdio_async_delegates_to_server() -> None:
    mock_server = AsyncMock()
    await run_stdio_async(mock_server)
    mock_server.run_stdio_async.assert_awaited_once()


def test_run_stdio_server_delegates_to_asyncio_run() -> None:
    mock_server = MagicMock()
    with (
        patch("hexastack_mcp.adapters.stdio.asyncio.run") as mock_run,
        patch("hexastack_mcp.adapters.stdio.run_stdio_async") as mock_async_fn,
    ):
        run_stdio_server(mock_server)
        assert mock_run.called
        assert mock_async_fn.called
