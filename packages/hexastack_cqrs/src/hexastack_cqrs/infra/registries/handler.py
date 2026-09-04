from typing import Any

from hexastack_core.domain import Generic
from hexastack_core.infra import (
    GenericHandlerRegistry,
    GenericHandlerRegistryError,
)
from hexastack_cqrs.ports.buses import HandlerDispatcherPort


class HandlerRegistryError(GenericHandlerRegistryError[Generic]):
    """Exception raised when handler registry lookup fails for a given generic message.

    Notes/Architectural Intent:
        Specializes generic handler lookup failures to provide clear diagnostics when dispatching commands/queries.
    """


class HandlerRegistry(GenericHandlerRegistry[Generic, Any], HandlerDispatcherPort):
    """Registry maintaining mappings from Generic message types to handler functions.

    Notes/Architectural Intent:
        Centralizes handler dispatch for CQRS messages, connecting commands and queries to their respective execution logic.
    """

    _error_cls = HandlerRegistryError
