"""Unit tests for devtools outbox commands."""

from unittest.mock import patch

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.outbox import add_outbox_commands


def test_outbox_commands():
    app = typer.Typer()
    add_outbox_commands(app)
    runner = CliRunner()

    res = runner.invoke(app, ["outbox", "--help"])
    assert res.exit_code == 0

    res_relay = runner.invoke(app, ["outbox", "relay", "--once"])
    assert res_relay.exit_code == 0
    assert "Drained and published 0 pending outbox events" in res_relay.output

    with patch("asyncio.run"):
        res_start = runner.invoke(app, ["outbox", "relay"])
        assert res_start.exit_code == 0

    with patch("asyncio.run", side_effect=KeyboardInterrupt):
        res_ctrl_c = runner.invoke(app, ["outbox", "relay"])
        assert res_ctrl_c.exit_code == 0
