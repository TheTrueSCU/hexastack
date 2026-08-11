import tomllib
from pathlib import Path

from pydantic import BaseModel

from hexastack_core.infra.config import HexastackConfig, HexastackCoreConfig


class ConfigRegistry:
    def __init__(self):
        self._core_schema: type[HexastackCoreConfig] = HexastackCoreConfig
        self._section_schemas: dict[str, type[BaseModel]] = {}

    def load(self, raw_file_path: str | Path = "hexastack.toml") -> HexastackConfig:
        file_path = Path(raw_file_path)

        raw_data: dict = {}

        with open(file_path, "rb") as f:
            raw_data = tomllib.load(f)

        core_data = raw_data.get("hexastack", {})
        core_config = self._core_schema(**core_data)

        section_configs: dict[str, BaseModel] = {}
        for name, schema in self._section_schemas.items():
            section_data = core_data.get(name, {})
            section_configs[name] = schema(**section_data)

        return HexastackConfig(core=core_config, sections=section_configs)


    def register_section(self, name: str, schema: type[BaseModel]) -> None:
        self._section_schemas[name] = schema
