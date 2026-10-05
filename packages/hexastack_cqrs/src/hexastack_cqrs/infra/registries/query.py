from typing import Any

from hexastack_core.domain import Query
from hexastack_core.infra import GenericTypeRegistry, GenericTypeRegistryError


class QueryRegistryError(GenericTypeRegistryError[Query[Any]]):
    """Exception raised when query type registry lookup fails.

    Notes/Architectural Intent:
        Provides specialized exception context when a requested Query subclass is unregistered.
    """


class QueryRegistry(GenericTypeRegistry[Query[Any]]):
    """Registry maintaining registered Query types in the application.

    Notes/Architectural Intent:
        Allows dynamic lookup and instantiation of Query classes by name across system boundaries.
    """

    _error_cls = QueryRegistryError
