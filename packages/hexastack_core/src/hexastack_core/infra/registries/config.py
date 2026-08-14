import tomllib
from pathlib import Path

from pydantic import BaseModel

from hexastack_core.infra.config import HexastackConfig, HexastackCoreConfig
from hexastack_core.infra.registries.generic import (
    GenericTypeRegistry,
    GenericTypeRegistryError,
)


class ConfigRegistryError(GenericTypeRegistryError[BaseModel]):
    """Exception raised when configuration section loading or lookup fails.

    Notes/Architectural Intent:
        Provides specialized exception context for configuration section resolution errors.
    """


class ConfigRegistry(GenericTypeRegistry[BaseModel]):
    """Registry maintaining registered configuration section schemas and parsing TOML files.

    Notes/Architectural Intent:
        Loads TOML configuration files into validated Pydantic models for core and package sections.
    """

    _error_cls = ConfigRegistryError

    def __init__(self) -> None:
        """Initialize ConfigRegistry with core configuration schema."""
        super().__init__()
        self._core_schema: type[HexastackCoreConfig] = HexastackCoreConfig

    def load_config_toml(
        self, raw_file_path: str | Path = "hexastack.toml"
    ) -> HexastackConfig:
        """Parse a TOML configuration file into a HexastackConfig instance.

        Args:
            raw_file_path: Path to the TOML configuration file. Defaults to "hexastack.toml".

        Returns:
            HexastackConfig object containing populated core and section models.

        Raises:
            FileNotFoundError: If the specified TOML file does not exist.
            tomllib.TOMLDecodeError: If the TOML file contains invalid syntax.
            pydantic.ValidationError: If configuration data fails schema validation.
        """
        file_path = Path(raw_file_path)

        with file_path.open("rb") as f:
            raw_data = tomllib.load(f)

        core_data = raw_data.get("hexastack", {})
        core_config = self._core_schema(**core_data)

        section_configs: dict[str, BaseModel] = {}
        for name, schema in self.all.items():
            section_data = core_data.get(name, {})
            section_configs[name] = schema(**section_data)

        return HexastackConfig(core=core_config, sections=section_configs)

    def register_config_section(self, name: str, schema: type[BaseModel]) -> None:
        """Register a package configuration section schema under name.

        Args:
            name: The section name key in TOML.
            schema: The Pydantic BaseModel class for the section.

        Returns:
            None.

        Raises:
            None.
        """
        self.register_by_name(schema, name)
