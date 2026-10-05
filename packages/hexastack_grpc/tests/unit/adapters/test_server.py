from unittest.mock import MagicMock

import grpc
import pytest

from hexastack_grpc.adapters.server import (
    create_async_grpc_server,
    run_grpc_server,
)


@pytest.mark.anyio
async def test_create_async_grpc_server():
    mock_interceptor = MagicMock(spec=grpc.aio.ServerInterceptor)
    server = create_async_grpc_server(
        host="127.0.0.1", port=50055, interceptors=[mock_interceptor]
    )
    assert server is not None
    await server.stop(grace=None)

    # Test with HexastackGrpcConfig object
    from hexastack_grpc.domain.config import HexastackGrpcConfig

    cfg = HexastackGrpcConfig(host="127.0.0.1", port=50057)
    server_cfg = create_async_grpc_server(config=cfg)
    assert server_cfg is not None
    await server_cfg.stop(grace=None)

    # Test with default args and interceptors=None fallback to empty tuple
    server_no_int = create_async_grpc_server(host="127.0.0.1", port=50056)
    assert server_no_int is not None
    await server_no_int.stop(grace=None)


def test_run_grpc_server_blocking_keyboard_interrupt():
    mock_server = MagicMock(spec=grpc.Server)
    mock_server.wait_for_termination.side_effect = KeyboardInterrupt()
    run_grpc_server(mock_server, block=True)
    mock_server.start.assert_called_once()
    mock_server.wait_for_termination.assert_called_once()
    mock_server.stop.assert_called_once_with(grace=5.0)


def test_run_grpc_server_blocking_normal():
    mock_server = MagicMock(spec=grpc.Server)
    run_grpc_server(mock_server, block=True)
    mock_server.start.assert_called_once()
    mock_server.wait_for_termination.assert_called_once()
    mock_server.stop.assert_not_called()


def test_run_grpc_server_non_blocking():
    mock_server = MagicMock(spec=grpc.Server)
    run_grpc_server(mock_server, block=False)
    mock_server.start.assert_called_once()
    mock_server.wait_for_termination.assert_not_called()
    mock_server.stop.assert_not_called()
    # Test default block argument (block=True by default)
    mock_server_def = MagicMock(spec=grpc.Server)
    run_grpc_server(mock_server_def)
    mock_server_def.wait_for_termination.assert_called_once()
