from unittest.mock import MagicMock, patch

from hexastack.entrypoint import main


def test_entrypoint_main():
    with (
        patch("hexastack.entrypoint.bootstrap") as mock_boot,
        patch("hexastack.adapters.cli.add_serve_command"),
    ):
        mock_cli = MagicMock()
        mock_boot.return_value = {"cli_app": mock_cli}
        main()
        assert mock_cli.called


def test_entrypoint_missing_cli_app():
    with (
        patch("hexastack.entrypoint.bootstrap") as mock_boot,
        patch("sys.exit") as mock_exit,
        patch("sys.stderr.write") as mock_write,
    ):
        mock_boot.return_value = {}
        main()
        assert mock_exit.called
        assert mock_write.called
