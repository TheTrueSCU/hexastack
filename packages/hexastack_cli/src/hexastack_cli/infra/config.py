from pydantic import BaseModel, Field

from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry


@config_section("cli")
class HexastackCliConfig(BaseModel):
    """Configuration schema for Hexastack CLI presentation adapter.

    Notes/Architectural Intent:
        Controls CLI application naming, versioning, Typer rich formatting, error traceback display,
        and automatic command discovery.
    """

    app_name: str = Field(default="hexastack")
    version: str = Field(default="0.1.0")
    help_text: str = Field(default="Hexastack CLI Application")
    auto_register_commands: bool = Field(default=True)
    rich_markup: bool = Field(default=True)
    show_exceptions: bool = Field(default=False)
    packages_to_scan: list[str] = Field(default_factory=list)


def register_cli_config(registry: ConfigRegistry) -> None:
    """Register CLI configuration schema with a ConfigRegistry under 'cli'.

    Args:
        registry: Target ConfigRegistry instance.

    Returns:
        None.

    Raises:
        None.
    """
    registry.register_config_section("cli", HexastackCliConfig)


__all__ = [
    "HexastackCliConfig",
    "register_cli_config",
]
