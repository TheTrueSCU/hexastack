from pydantic import BaseModel, Field


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


__all__ = [
    "HexastackCliConfig",
]
