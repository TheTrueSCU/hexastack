from unittest.mock import patch

import typer
from typer.testing import CliRunner

import hexastack.adapters.cli
import hexastack.application.diagnostics
from hexastack.adapters.cli import add_serve_command
from hexastack_core.infra.bootstrap import bootstrap


def test_cli_diagnostics_integration():
    result = bootstrap(
        packages_to_scan=[
            hexastack.application.diagnostics,
            hexastack.adapters.cli,
        ],
    )
    cli_app: typer.Typer = result.get("cli_app")
    assert cli_app is not None
    add_serve_command(cli_app)

    runner = CliRunner()

    # 1. Test info command
    res_info = runner.invoke(cli_app, ["info", "-o", "json"])
    assert res_info.exit_code == 0
    assert "hexastack-core" in res_info.stdout

    # 2. Test ping demo command
    res_ping = runner.invoke(cli_app, ["demo", "ping", "--message", "antigravity"])
    assert res_ping.exit_code == 0
    assert "antigravity" in res_ping.stdout

    # 3. Test /ping root alias
    res_alias = runner.invoke(cli_app, ["ping", "--message", "aliased"])
    assert res_alias.exit_code == 0
    assert "aliased" in res_alias.stdout

    # 4. Test serve command with mocked uvicorn
    with patch("uvicorn.run") as mock_run:
        res_serve = runner.invoke(cli_app, ["serve", "--no-reload", "--port", "9000"])
        assert res_serve.exit_code == 0
        assert mock_run.called

    # 5. Test ui command with mocked uvicorn
    from hexastack.adapters.cli import add_ui_commands

    add_ui_commands(cli_app)
    with patch("uvicorn.run") as mock_run_ui:
        res_ui = runner.invoke(cli_app, ["ui", "--port", "8080"])
        assert res_ui.exit_code == 0
        assert mock_run_ui.called
