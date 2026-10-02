from hexastack_core.domain import Command
from hexastack_core.infra import GenericTypeRegistry, GenericTypeRegistryError


class CommandRegistryError(GenericTypeRegistryError[Command]):
    """Exception raised when command type registry lookup fails.

    Notes/Architectural Intent:
        Provides specialized exception context when a requested Command subclass is unregistered.
    """


class CommandRegistry(GenericTypeRegistry[Command]):
    """Registry maintaining registered Command types in the application.

    Notes/Architectural Intent:
        Allows dynamic lookup and instantiation of Command classes by name across system boundaries.
    """

    _error_cls = CommandRegistryError
