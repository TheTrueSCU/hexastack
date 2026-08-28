"""Unit tests for devtools dev commands."""

from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.dev import (
    _start_fastapi_server,
    _start_grpc_server,
    _start_outbox_relay,
    add_dev_command,
)


def test_dev_commands():
    app = typer.Typer()
    add_dev_command(app)
    runner = CliRunner()

    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "host" in res.output

    with (
        patch("multiprocessing.Process.start"),
        patch("multiprocessing.Process.terminate"),
        patch("multiprocessing.Process.join"),
        patch(
            "hexastack.adapters.cli.devtools.commands.dev.time.sleep",
            side_effect=KeyboardInterrupt,
        ),
    ):
        res_dev = runner.invoke(app, ["--grpc", "--outbox"])
        assert res_dev.exit_code == 0


def test_dev_server_starters():
    with patch("uvicorn.run"):
        _start_fastapi_server("127.0.0.1", 8000)

    with (
        patch("hexastack_grpc.adapters.server.run_grpc_server"),
        patch("hexastack_core.infra.bootstrap.bootstrap") as mock_boot,
    ):
        mock_boot.return_value.container.resolve.return_value = MagicMock()
        _start_grpc_server("127.0.0.1", 50051)

    with patch("asyncio.run"):
        _start_outbox_relay(1.0, 50)
