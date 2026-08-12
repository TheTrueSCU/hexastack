from pydantic import BaseModel, Field

from hexastack_core.domain import HexastackError


class HexastackConfigError(HexastackError):
    """Exception raised when configuration section resolution or type validation fails.

    Notes/Architectural Intent:
        Specializes HexastackError for configuration loading and section retrieval failures.
    """


class HexastackCoreConfig(BaseModel):
    """Core application configuration model.

    Notes/Architectural Intent:
        Defines baseline configuration schema shared across all Hexastack services.
    """

    environment: str = Field(default="dev")
    app_name: str = Field(default="hexastack-app")
    debug: bool = Field(default=False)


class HexastackConfig:
    """Aggregated application configuration container holding core and package sections.

    Notes/Architectural Intent:
        Encapsulates section retrieval with runtime type checking.
    """

    def __init__(self, core: HexastackCoreConfig, sections: dict[str, BaseModel]):
        """Initialize HexastackConfig container.

        Args:
            core: HexastackCoreConfig instance.
            sections: Dictionary mapping section names to section BaseModel instances.
        """
        self._core = core
        self._sections = sections

    def get_section[T: BaseModel](
        self, section_name: str, expected_type: type[T]
    ) -> T:
        """Retrieve a specific package configuration section by name.

        Args:
            section_name: The section name key.
            expected_type: Expected BaseModel subclass.

        Returns:
            The requested section configuration object of type T.

        Raises:
            HexastackConfigError: If section_name is not registered or is not of expected_type.
        """
        if not (section := self._sections.get(section_name)):
            raise HexastackConfigError(
                f"Config section '{section_name}' not registered."
            )

        if not isinstance(section, expected_type):
            raise HexastackConfigError(
                f"Section '{section_name}' is not of type '{expected_type.__name__}'; received '{type(section).__name__}'"
            )

        return section
