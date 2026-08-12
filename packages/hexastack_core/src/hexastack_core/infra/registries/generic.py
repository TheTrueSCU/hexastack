from collections.abc import Callable
from typing import Any

from hexastack_core.domain import HexastackRegistryError


class GenericHandlerRegistryError[T](HexastackRegistryError):
    """Exception raised when no handler is registered for a target class.

    Notes/Architectural Intent:
        Provides clear exception messaging when looking up or executing a handler for an unhandled class.
    """

    def __init__(self, cls: type[Any]):
        """Initialize exception with target class name.

        Args:
            cls: The target class missing a registered handler.
        """
        super().__init__(f"No handler registered for '{cls.__name__}'")


class GenericHandlerRegistry[T, P]:
    """Generic registry mapping input types T to handler functions returning P.

    Notes/Architectural Intent:
        Encapsulates generic handler lookup, polymorphism fallback, and invocation across domain boundaries.
    """

    _error_cls: type[GenericHandlerRegistryError[T]] = GenericHandlerRegistryError[T]

    def __init__(self) -> None:
        """Initialize empty handler registry."""
        self._mapper: dict[type[Any], Callable[[Any], P]] = {}

    def __contains__(self, cls: type[Any]) -> bool:
        """Check if a handler is registered for class cls or any of its superclasses.

        Args:
            cls: Class type to verify.

        Returns:
            True if a matching handler is found, otherwise False.
        """
        return self.get(cls) is not None

    @property
    def all(self) -> dict[type[Any], Callable[[Any], P]]:
        """Dictionary of all registered class-to-handler mappings.

        Returns:
            Shallow copy of current registry mapping dictionary.
        """
        return dict(self._mapper)

    def clear(self) -> None:
        """Clear all registered handlers from the registry.

        Returns:
            None.

        Raises:
            None.
        """
        self._mapper.clear()

    def get(
        self, cls: type[T], exact: bool = False
    ) -> Callable[[Any], P] | None:
        """Retrieve handler callable registered for class cls.

        Args:
            cls: Target class to look up.
            exact: If True, requires exact class match without subclass checking.

        Returns:
            The registered handler function if found, otherwise None.

        Raises:
            None.
        """
        if handler := self._mapper.get(cls):
            return handler

        if exact:
            return None

        for registered_cls, handler in self._mapper.items():
            if issubclass(cls, registered_cls):
                return handler

        return None

    def handle(
        self, instance: T, exact: bool = False, reraise: bool = True
    ) -> P | None:
        """Execute the handler corresponding to instance.

        Args:
            instance: Input object to be handled.
            exact: If True, requires exact class match.
            reraise: If True, raises _error_cls when no handler is found.

        Returns:
            The result of handler execution, or None if no handler found and reraise=False.

        Raises:
            GenericHandlerRegistryError: If no handler is registered and reraise=True.
        """
        if handler := self.get(type(instance), exact=exact):
            return handler(instance)

        if reraise:
            if instance and isinstance(instance, BaseException):
                raise self._error_cls(type(instance)) from instance

            raise self._error_cls(type(instance))

        return None

    def register(self, cls: type[Any], handler: Callable[[Any], P]) -> None:
        """Register a handler function for class cls.

        Args:
            cls: The target class key.
            handler: Callable handling instances of cls.

        Returns:
            None.

        Raises:
            None.
        """
        self._mapper[cls] = handler


class GenericTypeRegistryError[T](HexastackRegistryError):
    """Exception raised when a requested named type is not registered.

    Notes/Architectural Intent:
        Provides clear exception context when looking up unregistered type metadata.
    """

    def __init__(self, name: str):
        """Initialize exception with type name.

        Args:
            name: The lookup key name.
        """
        super().__init__(f"Type '{name}' is not registered.")


class GenericTypeRegistry[T]:
    """Generic registry mapping string names to class types T.

    Notes/Architectural Intent:
        Enables name-based dynamic lookup and instantiation of generic types.
    """

    _error_cls: type[GenericTypeRegistryError[T]] = GenericTypeRegistryError[T]

    def __init__(self) -> None:
        """Initialize empty generic type registry."""
        self._mapper: dict[str, type[T]] = {}

    def __contains__(self, name: str) -> bool:
        """Check if a type is registered under name.

        Args:
            name: String identifier.

        Returns:
            True if name is registered, otherwise False.
        """
        return name in self._mapper

    @property
    def all(self) -> dict[str, type[T]]:
        """Dictionary of all registered name to type mappings.

        Returns:
            Shallow copy of current registry mapping dictionary.
        """
        return dict(self._mapper)

    def clear(self) -> None:
        """Clear all registered types from the registry.

        Returns:
            None.

        Raises:
            None.
        """
        self._mapper.clear()

    def get(self, name: str) -> type[T]:
        """Retrieve registered type by name.

        Args:
            name: The string identifier.

        Returns:
            The registered class type.

        Raises:
            GenericTypeRegistryError: If no type is registered under name.
        """
        if not (cls := self._mapper.get(name)):
            raise self._error_cls(name)

        return cls

    def register(self, cls: type[T]) -> None:
        """Register a class using its class __name__.

        Args:
            cls: The class type to register.

        Returns:
            None.

        Raises:
            None.
        """
        self.register_by_name(cls, cls.__name__)

    def register_by_name(self, cls: type[T], name: str) -> None:
        """Register a class under an explicit string name.

        Args:
            cls: The class type.
            name: Custom string name identifier.

        Returns:
            None.

        Raises:
            None.
        """
        self._mapper[name] = cls
