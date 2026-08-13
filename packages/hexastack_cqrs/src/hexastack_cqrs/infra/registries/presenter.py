from typing import Any

from hexastack_core.domain import Generic, HexastackRegistryError
from hexastack_core.ports import PresenterPort


class PresenterRegistryError(HexastackRegistryError):
    """Exception raised when looking up an unregistered Presenter format mapping.

    Notes/Architectural Intent:
        Provides explicit error messaging when presentation layer conversion is missing for a model.
    """

    def __init__(self, instance: Generic, output_format: str) -> None:
        """Initialize exception with instance type and format string.

        Args:
            instance: The generic domain object being presented.
            output_format: Requested output format identifier (e.g., 'json', 'html').
        """
        message = (
            f"No Presenter registered for {type(instance).__name__} as {output_format}."
        )
        super().__init__(message)


class PresenterRegistry:
    """Registry managing Presenter instances indexed by domain class and output format.

    Notes/Architectural Intent:
        Maps domain response models to format-specific PresenterPort instances.
    """

    def __init__(self) -> None:
        """Initialize empty presenter registry."""
        self._mapper: dict[tuple[type[Generic], str], PresenterPort] = {}

    def __contains__(self, key: tuple[type[Generic], str]) -> bool:
        """Check if a Presenter is registered for the (class, format) key."""
        return key in self._mapper

    @property
    def all(self) -> dict[tuple[type[Generic], str], PresenterPort]:
        """Dictionary of all registered (class, format) to Presenter mappings."""
        return dict(self._mapper)

    def clear(self) -> None:
        """Clear all registered Presenter mappings from the registry."""
        self._mapper.clear()

    def get(self, cls: type[Generic], output_format: str) -> PresenterPort | None:
        """Retrieve Presenter registered for domain class cls and output_format."""
        return self._mapper.get((cls, output_format))

    def present(
        self,
        instance: Generic,
        output_format: str,
        reraise: bool = True,
    ) -> Any | None:
        """Present instance in requested output_format using registered Presenter."""
        if presenter := self.get(type(instance), output_format):
            return presenter.present(instance)

        if reraise:
            raise PresenterRegistryError(instance, output_format)

        return None

    def register(
        self, cls: type[Generic], output_format: str, presenter: PresenterPort
    ) -> None:
        """Register a Presenter instance for class cls and output_format."""
        self._mapper[(cls, output_format)] = presenter


__all__ = [
    "PresenterRegistry",
    "PresenterRegistryError",
]
