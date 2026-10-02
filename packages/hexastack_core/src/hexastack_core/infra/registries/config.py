import os
import tomllib
from collections import ChainMap
from collections.abc import Mapping
from pathlib import Path
from typing import Any

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
        Leverages collections.ChainMap to provide zero-copy multi-tier configuration resolution
        across runtime overrides, environment variables, TOML file data, and schema defaults.
    """

    _error_cls = ConfigRegistryError

    def __init__(self) -> None:
        """Initialize ConfigRegistry with core configuration schema."""
        super().__init__()
        self._core_schema: type[HexastackCoreConfig] = HexastackCoreConfig

    def load_config_layered(
        self,
        raw_file_path: str | Path | None = "hexastack.toml",
        overrides: Mapping[str, Any] | None = None,
        env_vars: Mapping[str, str] | None = None,
        env_prefix: str = "HEXASTACK_",
    ) -> HexastackConfig:
        """Parse configuration combining TOML file, environment variables, and overrides using ChainMap.

        Args:
            raw_file_path: Optional path to the TOML configuration file. If None or file doesn't exist,
                file layer is treated as empty.
            overrides: Optional highest-precedence runtime/CLI dictionary overrides.
            env_vars: Optional environment variable mapping. Defaults to os.environ.
            env_prefix: Environment variable prefix for scoping (default 'HEXASTACK_').

        Returns:
            HexastackConfig object containing validated core and section models.

        Raises:
            tomllib.TOMLDecodeError: If the TOML file exists but contains invalid syntax.
            pydantic.ValidationError: If merged configuration fails schema validation.

        Notes/Architectural Intent:
            Uses collections.ChainMap to overlay overrides -> environment -> TOML without
            expensive deep copying or destructive dictionary mutations.
        """
        raw_toml: dict[str, Any] = {}
        if raw_file_path is not None:
            file_path = Path(raw_file_path)
            if file_path.exists():
                with file_path.open("rb") as f:
                    raw_toml = tomllib.load(f)

        raw_core_toml = raw_toml.get("hexastack", {})

        # Extract environment variables matching prefix
        active_env = os.environ if env_vars is None else env_vars
        core_env: dict[str, Any] = {}
        section_envs: dict[str, dict[str, Any]] = {name: {} for name in self.all}

        for k, v in active_env.items():
            if not k.startswith(env_prefix):
                continue
            stripped = k[len(env_prefix) :].lower()
            if "__" in stripped:
                sec_part, key_part = stripped.split("__", 1)
                if sec_part in ("core", "hexastack"):
                    core_env[key_part] = v
                elif sec_part in section_envs:
                    section_envs[sec_part][key_part] = v
            else:
                core_env[stripped] = v

        # Build layered mapping for core
        core_overrides = dict(overrides.get("hexastack", {})) if overrides else {}
        core_chain = ChainMap(core_overrides, core_env, raw_core_toml)
        core_config = self._core_schema(**dict(core_chain))

        # Build layered mappings for registered sections
        section_configs: dict[str, BaseModel] = {}
        for name, schema in self.all.items():
            sec_overrides = dict(overrides.get(name, {})) if overrides else {}
            sec_env = section_envs.get(name, {})
            sec_toml = (
                raw_core_toml.get(name, {}) if isinstance(raw_core_toml, dict) else {}
            )
            sec_chain = ChainMap(sec_overrides, sec_env, sec_toml)
            section_configs[name] = schema(**dict(sec_chain))

        return HexastackConfig(core=core_config, sections=section_configs)

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
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {raw_file_path}")

        return self.load_config_layered(raw_file_path=file_path)

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
