from typing import Any

from hexastack_core.infra.registries.generic import (
    GenericHandlerRegistry,
    GenericHandlerRegistryError,
)


class ExceptionRegistryError(GenericHandlerRegistryError[BaseException]):
    """Exception raised when no exception handler is registered for an exception type.

    Notes/Architectural Intent:
        Provides exception context when mapping raised exceptions to error response dicts fails.
    """


class ExceptionRegistry(GenericHandlerRegistry[BaseException, dict[str, Any]]):
    """Registry mapping BaseException subclasses to exception formatting handlers.

    Notes/Architectural Intent:
        Centralizes exception translation into standardized error dictionaries for presentation layers.
    """

    _error_cls = ExceptionRegistryError
