import types
from typing import Any, cast

import typer
from typer.testing import CliRunner

from hexastack_cli.infra.bootstrap import CliBootstrapper
from hexastack_cli.infra.config import HexastackCliConfig
from hexastack_cli.infra.decorators import cli_command
from hexastack_core.domain import Command, Generic
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_cqrs.infra.bootstrap import CqrsBootstrapper
from hexastack_cqrs.infra.decorators import command_handler
from hexastack_logging.infra.bootstrap import LoggingBootstrapper


@cli_command("ping", help="Ping system")
class PingCmd(Command):
    message: str = "pong"


class PingDTO(Generic):
    reply: str


@command_handler(PingCmd)
class PingHandler:
    def __call__(self, cmd: PingCmd) -> PingDTO:
        return PingDTO(reply=f"PONG: {cmd.message}")


def test_cli_bootstrapper_registration():
    reg = ConfigRegistry()
    bootstrapper = CliBootstrapper()
    bootstrapper.register_config(reg)

    assert "cli" in reg
    assert reg.get("cli") == HexastackCliConfig


def test_meta_bootstrap_with_cli_and_autodiscovery():
    mod = types.ModuleType("sample_ping_mod")
    cast("Any", mod).PingCmd = PingCmd
    cast("Any", mod).PingHandler = PingHandler

    result = bootstrap(
        bootstrappers=[
            LoggingBootstrapper(),
            CqrsBootstrapper(),
            CliBootstrapper(),
        ],
        packages_to_scan=[mod],
        auto_discover=False,
    )

    assert typer.Typer in result.container
    cli_app = result.get("cli_app")
    assert isinstance(cli_app, typer.Typer)

    runner = CliRunner()
    res = runner.invoke(cli_app, ["ping", "--message", "hello"])
    assert res.exit_code == 0
    assert "PONG: hello" in res.stdout


def test_cli_bootstrapper_configure_standalone():
    """Verify CliBootstrapper configure with pipeline in container and config present."""
    from rodi import Container

    from hexastack_core.infra.bootstrap import BootstrapContext
    from hexastack_cqrs.infra.pipeline import ExecutionPipeline
    from hexastack_cqrs.infra.registries.handler import HandlerRegistry

    container = Container()
    pipeline = ExecutionPipeline(handler_registry=HandlerRegistry())
    container.add_instance(pipeline, declared_class=ExecutionPipeline)

    bootstrapper = CliBootstrapper()
    config_reg = ConfigRegistry()
    bootstrapper.register_config(config_reg)

    ctx = BootstrapContext(container=container, config=None, config_registry=config_reg)
    bootstrapper.configure(ctx)

    assert "cli_app" in ctx.properties
    assert isinstance(ctx.properties["cli_app"], typer.Typer)
