
from pydantic import BaseModel, Field


class HexastackCoreConfig(BaseModel):
    environment: str = Field(default="dev")
    app_name: str = Field(default="hexastack-app")
    debug: bool = Field(default=False)


class HexastackConfig:
    def __init__(self, core: HexastackCoreConfig, sections: dict[str, BaseModel]):
        self._core = core
        self._sections = sections

    def get_section(self, section_name: str, expected_type: type[BaseModel]) -> BaseModel:
        if not (section := self._sections.get(section_name)):
            raise KeyError(f"Config section '{section_name}' not registered.")

        if not isinstance(section, expected_type):
            raise TypeError(f"Section '{section_name}' is not of type '{expected_type.__name__}'; received '{type(section).__name__}'")

        return section


