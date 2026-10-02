"""Unit tests for devtools dev commands."""

from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.dev import (
    _start_fastapi_server,
    _start_grpc_server,
    _start_outbox_relay,
    _start_zrok_share,
    add_dev_command,
)


def test_dev_commands():
    app = typer.Typer()
    add_dev_command(app)
    runner = CliRunner()

    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "host" in res.output
    assert "share" in res.output

    with (
        patch("multiprocessing.Process.start"),
        patch("multiprocessing.Process.terminate"),
        patch("multiprocessing.Process.join"),
        patch(
            "hexastack.adapters.cli.devtools.commands.dev.time.sleep",
            side_effect=KeyboardInterrupt,
        ),
        patch(
            "hexastack.adapters.cli.devtools.commands.dev._start_zrok_share"
        ) as mock_share,
    ):
        mock_proc = MagicMock()
        mock_share.return_value = mock_proc
        res_dev = runner.invoke(
            app, ["--grpc", "--outbox", "--share", "--share-mode", "private"]
        )
        assert res_dev.exit_code == 0
        mock_share.assert_called_once_with("127.0.0.1", 8000, "private")
        mock_proc.terminate.assert_called_once()


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


def test_start_zrok_share_missing_binary():
    with patch("shutil.which", return_value=None):
        proc = _start_zrok_share("127.0.0.1", 8000, "public")
        assert proc is None


def test_start_zrok_share_success():
    with (
        patch("shutil.which", return_value="/usr/local/bin/zrok"),
        patch("subprocess.Popen") as mock_popen,
    ):
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc
        proc = _start_zrok_share("127.0.0.1", 8000, "public")
        assert proc == mock_proc
        mock_popen.assert_called_once()
