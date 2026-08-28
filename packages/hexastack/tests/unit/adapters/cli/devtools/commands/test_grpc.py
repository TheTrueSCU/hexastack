"""Unit tests for devtools grpc commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.grpc import (
    _exec_grpc_compile,
    _exec_grpc_list,
    _exec_grpc_serve,
    add_grpc_commands,
)


def test_grpc_commands():
    app = typer.Typer()
    add_grpc_commands(app)
    runner = CliRunner()

    res = runner.invoke(app, ["grpc", "--help"])
    assert res.exit_code == 0

    res_list = runner.invoke(app, ["grpc", "list"])
    assert res_list.exit_code == 0

    with patch(
        "hexastack_grpc.infra.compiler.ProtoCompiler.compile_files", return_value=[]
    ):
        res_compile = runner.invoke(app, ["grpc", "compile"])
        assert res_compile.exit_code == 0

    with patch("hexastack.adapters.cli.devtools.commands.grpc._exec_grpc_serve"):
        res_serve = runner.invoke(app, ["grpc", "serve", "--port", "50055"])
        assert res_serve.exit_code == 0

    with (
        patch("shutil.which", return_value="/usr/bin/buf"),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value.returncode = 0
        res_lint = runner.invoke(app, ["grpc", "lint"])
        assert res_lint.exit_code == 0

        res_breaking = runner.invoke(app, ["grpc", "breaking"])
        assert res_breaking.exit_code == 0

    with patch("shutil.which", return_value=None):
        res_no_buf = runner.invoke(app, ["grpc", "lint"])
        assert res_no_buf.exit_code == 1

        res_no_buf_b = runner.invoke(app, ["grpc", "breaking"])
        assert res_no_buf_b.exit_code == 1


def test_grpc_helper_executors():
    with (
        patch("hexastack_grpc.adapters.server.run_grpc_server"),
        patch("hexastack_core.infra.bootstrap.bootstrap") as mock_boot,
    ):
        mock_boot.return_value.container.resolve.return_value = MagicMock()
        _exec_grpc_serve("0.0.0.0", 50051)

    with (
        patch(
            "hexastack_grpc.infra.compiler.ProtoCompiler.compile_files",
            return_value=[Path("test_pb2.py")],
        ),
        patch("hexastack_grpc.infra.registries.proto.get_proto_registry") as mock_p_reg,
    ):
        mock_p_reg.return_value.entries = []
        _exec_grpc_compile("src/generated", proto_file=["test.proto"])

    _exec_grpc_list()
