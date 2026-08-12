from abc import ABC, abstractmethod
from typing import Any

from hexastack_core.domain import Generic


class Presenter(ABC):
    """Abstract base class for output representation presenters.

    Notes/Architectural Intent:
        Transforms domain objects into target output formats (e.g. JSON DTOs, HTML, CLI text).
    """

    @abstractmethod
    def present(self, instance: Generic) -> Any | None:
        """Format a generic domain instance into presenter output.

        Args:
            instance: The generic domain object instance to format.

        Returns:
            The presented view object or formatted data, or None.

        Raises:
            PresenterRegistryError: If formatting fails.
        """
        ...
