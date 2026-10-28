"""Unit tests for devtools serve commands."""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.serve import add_serve_command
from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_fastapi.testing.server import find_free_port


def test_serve_commands(tmp_path: Path):
    app = typer.Typer()
    add_serve_command(app)
    runner = CliRunner()

    res = runner.invoke(app, ["--help"])
    clean_output = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", res.output)
    assert res.exit_code == 0
    assert "host" in clean_output
    assert "engine" in clean_output
    assert "workers" in clean_output
    assert "ziti-identity" in clean_output

    port_1 = find_free_port()
    with patch("hexastack_fastapi.adapters.server.run_server") as mock_server:
        res_default = runner.invoke(app, ["--port", str(port_1)])
        assert res_default.exit_code == 0
        mock_server.assert_called_once_with(
            "hexastack.adapters.fastapi:create_demo_app",
            engine="uvicorn",
            host="127.0.0.1",
            port=port_1,
            reload=True,
            workers=None,
            factory=True,
        )

    port_2 = find_free_port()
    with patch("hexastack_fastapi.adapters.server.run_server") as mock_server:
        res_granian = runner.invoke(
            app, ["--engine", "granian", "--workers", "4", "--port", str(port_2)]
        )
        assert res_granian.exit_code == 0
        mock_server.assert_called_once_with(
            "hexastack.adapters.fastapi:create_demo_app",
            engine="granian",
            host="127.0.0.1",
            port=port_2,
            reload=True,
            workers=4,
            factory=True,
        )

    # Test OpenZiti dark serving with uvicorn
    id_file = tmp_path / "ziti.json"
    id_file.write_text("{}", encoding="utf-8")

    mock_adapter = MagicMock()
    with patch(
        "hexastack_fastapi.adapters.openziti.OpenZitiASGIAdapter",
        return_value=mock_adapter,
    ):
        res_ziti = runner.invoke(
            app,
            ["--ziti-identity", str(id_file), "--ziti-service", "custom-svc"],
        )
        assert res_ziti.exit_code == 0
        assert "Zero-Trust Dark Service" in res_ziti.output
        mock_adapter.run_uvicorn.assert_called_once()

    # Test OpenZiti rejects granian engine
    res_ziti_granian = runner.invoke(
        app,
        ["--ziti-identity", str(id_file), "--engine", "granian"],
    )
    assert res_ziti_granian.exit_code != 0
    assert "OpenZiti overlay requires 'uvicorn' engine" in res_ziti_granian.output

    # Test MissingDependencyError when fastapi is missing
    with (
        patch("importlib.util.find_spec", return_value=None),
        pytest.raises(MissingDependencyError),
    ):
        runner.invoke(app, [], catch_exceptions=False)
