import typer
from hexastack_core.domain import Generic
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_cqrs.infra.registries.presenter import PresenterRegistry
from rich.console import Console
from rodi import Container

from hexastack_cli.adapters.presenter import RichTerminalPresenter
from hexastack_cli.infra.config import HexastackCliConfig


def create_cli_app(
    config: HexastackCliConfig | None = None,
    container: Container | None = None,
    pipeline: ExecutionPipeline | None = None,
    console: Console | None = None,
) -> typer.Typer:
    """Factory creating and configuring a Typer CLI application integrated with Hexastack.

    Notes/Architectural Intent:
        Assembles a Typer CLI instance configured with Rich formatting, binds container
        and pipeline references, supports top-level --version, ensures multi-command dispatching,
        and registers terminal presenters into the presenter registry.

    Args:
        config: Optional HexastackCliConfig instance.
        container: Optional rodi Container instance.
        pipeline: Optional ExecutionPipeline instance.
        console: Optional rich Console instance.

    Returns:
        Configured Typer application instance.

    Raises:
        None.
    """
    cfg = config or HexastackCliConfig()
    active_console = console or Console()

    app = typer.Typer(
        name=cfg.app_name,
        help=cfg.help_text,
        rich_markup_mode="rich" if cfg.rich_markup else None,
        no_args_is_help=True,
    )

    def _version_callback(value: bool) -> None:
        if value:
            active_console.print(f"{cfg.app_name} {cfg.version}")
            raise typer.Exit()

    # Establish root callback to enforce multi-command structure and handle --version
    @app.callback()
    def _main(
        version: bool | None = typer.Option(
            None,
            "--version",
            "-v",
            help="Show the application version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ) -> None:
        pass

    # Register RichTerminalPresenter if presenter registry is present in DI
    if container is not None and PresenterRegistry in container:
        pres_reg = container.resolve(PresenterRegistry)
        terminal_presenter = RichTerminalPresenter(console=active_console)
        pres_reg.register(Generic, "rich", terminal_presenter)
        container.add_instance(terminal_presenter, declared_class=RichTerminalPresenter)

    return app


__all__ = [
    "create_cli_app",
]
