import typer
from rodi import Container
from typer.testing import CliRunner

from hexastack_cli.adapters.app import create_cli_app
from hexastack_cli.adapters.presenter import RichTerminalPresenter
from hexastack_cli.infra.config import HexastackCliConfig
from hexastack_cqrs.infra.registries.presenter import PresenterRegistry


def test_create_cli_app_defaults():
    container = Container()
    pres_reg = PresenterRegistry()
    container.add_instance(pres_reg, declared_class=PresenterRegistry)

    cfg = HexastackCliConfig(app_name="my-tool", version="1.2.3", help_text="My Tool")
    app = create_cli_app(config=cfg, container=container)

    assert isinstance(app, typer.Typer)
    assert RichTerminalPresenter in container

    runner = CliRunner()
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "my-tool 1.2.3" in res.stdout
