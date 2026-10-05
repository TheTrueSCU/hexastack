"""Unit tests for devtools serve commands."""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.serve import add_serve_command
from hexastack_core.domain.exceptions import MissingDependencyError


def test_serve_commands(tmp_path: Path):
    app = typer.Typer()
    add_serve_command(app)
    runner = CliRunner()

    res = runner.invoke(app, ["--help"])
    clean_output = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", res.output)
    assert res.exit_code == 0
    assert "host" in clean_output
    assert "ziti-identity" in clean_output

    with patch("uvicorn.run") as mock_uvicorn:
        res_run = runner.invoke(app, ["--no-reload"])
        assert res_run.exit_code == 0
        mock_uvicorn.assert_called_once()

    # Test OpenZiti dark serving
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

    # Test MissingDependencyError when uvicorn is missing
    with (
        patch("importlib.util.find_spec", return_value=None),
        pytest.raises(MissingDependencyError),
    ):
        runner.invoke(app, [], catch_exceptions=False)
