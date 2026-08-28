"""Unit tests for devtools db commands."""

from unittest.mock import patch

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.db import add_db_commands


def test_db_commands():
    app = typer.Typer()
    add_db_commands(app)
    runner = CliRunner()

    res = runner.invoke(app, ["db", "--help"])
    assert res.exit_code == 0
    assert "init" in res.output
    assert "revision" in res.output
    assert "upgrade" in res.output

    with patch("hexastack_db.infra.migrations.init_migrations") as mock_init:
        res = runner.invoke(app, ["db", "init", "custom_mig"])
        assert res.exit_code == 0
        mock_init.assert_called_once_with("custom_mig")

    with patch("hexastack_db.infra.migrations.run_upgrade") as mock_upgrade:
        res = runner.invoke(app, ["db", "migrate"])
        assert res.exit_code == 0
        assert mock_upgrade.called

    with patch("hexastack_db.infra.migrations.run_check") as mock_check:
        res = runner.invoke(app, ["db", "check"])
        assert res.exit_code == 0
        assert mock_check.called

    with patch(
        "hexastack_db.infra.migrations.run_check", side_effect=Exception("drift")
    ):
        res = runner.invoke(app, ["db", "check"])
        assert res.exit_code == 1

    with patch("hexastack_db.infra.migrations.run_revision") as mock_rev:
        res = runner.invoke(app, ["db", "revision", "create_users_table"])
        assert res.exit_code == 0
        assert mock_rev.called

    with patch("hexastack_db.infra.migrations.run_current") as mock_curr:
        res = runner.invoke(app, ["db", "current"])
        assert res.exit_code == 0
        assert mock_curr.called

    with patch("hexastack_db.infra.migrations.run_history") as mock_hist:
        res = runner.invoke(app, ["db", "history"])
        assert res.exit_code == 0
        assert mock_hist.called

    with patch("hexastack_db.infra.migrations.stamp") as mock_stamp:
        res = runner.invoke(app, ["db", "stamp", "head"])
        assert res.exit_code == 0
        assert mock_stamp.called
