"""Abstract dependency injection container ports and protocols.

Notes/Architectural Intent:
    Defines the universal inversion-of-control container interface for Hexastack.
    Allows application bootstrappers, CQRS pipelines, and transport adapters to interact
    with either full-featured desktop/cloud containers (like `rodi`) or embedded zero-overhead
    containers (like `MicroContainer`) interchangeably without architectural drift.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, overload, runtime_checkable

T = TypeVar("T")
R = TypeVar("R")


@runtime_checkable
class ContainerPort(Protocol):
    """Universal dependency injection container protocol.

    Notes/Architectural Intent:
        Standardizes service registration and reflection resolution across
        both `rodi.Container` and `MicroContainer`.
    """

    def add_instance(
        self,
        instance: Any,
        declared_class: type | None = None,
    ) -> Any:
        """Register a pre-constructed instance into the container.

        Args:
            instance: Pre-instantiated object.
            declared_class: Optional abstract interface or base class.

        Returns:
            Container instance for chaining.
        """
        ...

    def add_singleton(
        self,
        base_type: Any,
        concrete_type: Any = None,
    ) -> Any:
        """Register a singleton service resolved once and memoized.

        Args:
            base_type: Class or interface to bind, or factory callable.
            concrete_type: Optional concrete class implementation.

        Returns:
            Container instance for chaining.
        """
        ...

    def add_transient(
        self,
        base_type: Any,
        concrete_type: Any = None,
    ) -> Any:
        """Register a transient service freshly instantiated on every resolve.

        Args:
            base_type: Class or interface to bind, or factory callable.
            concrete_type: Optional concrete class implementation.

        Returns:
            Container instance for chaining.
        """
        ...

    def add_scoped(
        self,
        base_type: Any,
        concrete_type: Any = None,
    ) -> Any:
        """Register a scoped service.

        Args:
            base_type: Class or interface to bind, or factory callable.
            concrete_type: Optional concrete class implementation.

        Returns:
            Container instance for chaining.
        """
        ...

    def register(
        self,
        obj_type: type | str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Register a service conforming to container protocols.

        Args:
            obj_type: Type or name to register.
            args: Positional factory arguments.
            kwargs: Keyword factory arguments.
        """
        ...

    @overload
    def resolve[R](self, obj_type: type[R], *args: Any, **kwargs: Any) -> R: ...

    @overload
    def resolve(self, obj_type: str, *args: Any, **kwargs: Any) -> Any: ...

    def resolve(
        self,
        obj_type: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Resolve and return an instance of the requested service type or key.

        Args:
            obj_type: Class, interface, or name to resolve.
            args: Optional positional arguments for instantiation.
            kwargs: Optional keyword arguments for instantiation.

        Returns:
            Activated service instance.
        """
        ...

    def build_provider(self) -> Any:
        """Build and return the activated service provider.

        Returns:
            Service provider instance.
        """
        ...

    def __contains__(self, item: Any, /) -> bool:
        """Check if a service or interface is registered.

        Args:
            item: Class type or identifier.

        Returns:
            True if configured, False otherwise.
        """
        ...


__all__ = [
    "ContainerPort",
]
