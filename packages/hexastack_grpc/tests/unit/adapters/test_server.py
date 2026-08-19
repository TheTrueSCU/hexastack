from unittest.mock import MagicMock

import grpc
import pytest

from hexastack_grpc.adapters.server import (
    create_async_grpc_server,
    run_grpc_server,
)
from hexastack_grpc.infra.config import HexastackGrpcConfig


@pytest.mark.anyio
async def test_create_async_grpc_server():
    cfg = HexastackGrpcConfig(host="127.0.0.1", port=50055)
    mock_interceptor = MagicMock(spec=grpc.aio.ServerInterceptor)
    server = create_async_grpc_server(config=cfg, interceptors=[mock_interceptor])
    assert server is not None
    await server.stop(grace=None)


def test_run_grpc_server_non_blocking():
    mock_server = MagicMock(spec=grpc.Server)
    run_grpc_server(mock_server, block=False)
    mock_server.start.assert_called_once()
    mock_server.wait_for_termination.assert_not_called()


def test_run_grpc_server_blocking_keyboard_interrupt():
    mock_server = MagicMock(spec=grpc.Server)
    mock_server.wait_for_termination.side_effect = KeyboardInterrupt()
    run_grpc_server(mock_server, block=True)
    mock_server.start.assert_called_once()
    mock_server.wait_for_termination.assert_called_once()
    mock_server.stop.assert_called_once_with(grace=5.0)
