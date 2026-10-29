"""Lightweight pure-Python dependency injection container for edge and embedded execution.

Notes/Architectural Intent:
    Provides a zero-dependency, pure-Python IoC container adhering to ContainerPort.
    Designed for resource-constrained embedded runtimes (MicroPython, WebAssembly Pyodide/WASI)
    where third-party libraries like `rodi` or C-extensions are absent or memory-prohibitive.
    Supports constructor reflection via inspect.signature, singletons, transients, and pre-instantiated services.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar, overload

from hexastack_core.utils.runtime import is_edge, is_micropython, is_wasm

if TYPE_CHECKING:
    from hexastack_core.ports.container import ContainerPort

T = TypeVar("T")


class ContainerException(Exception):
    """Base exception for container configuration and resolution failures."""


class CannotResolveException(ContainerException):
    """Exception raised when a requested type cannot be activated or resolved."""

    def __init__(self, target: Any) -> None:
        name = getattr(target, "__name__", str(target))
        super().__init__(f"Unable to resolve service or type '{name}'.")


class MicroContainer:
    """Lightweight zero-dependency dependency injection container for edge runtimes.

    Notes/Architectural Intent:
        Implements the essential subset of `ContainerPort` without external dependencies.
        Allows full CQRS bus pipelines and hexagonal adapter graphs to resolve on WebAssembly
        and MicroPython targets with minimal memory overhead (<10KB).
    """

    def __init__(self) -> None:
        """Initialize empty MicroContainer registry."""
        self._instances: dict[Any, Any] = {}
        self._factories: dict[Any, tuple[Callable[..., Any], bool]] = {}

    def add_instance(
        self,
        instance: Any,
        declared_class: type | None = None,
    ) -> MicroContainer:
        """Register a pre-constructed instance into the container.

        Args:
            instance: The pre-instantiated object.
            declared_class: Optional abstract base or protocol interface type.

        Returns:
            self for fluent chaining.
        """
        concrete_cls = type(instance)
        self._instances[concrete_cls] = instance
        self._instances[concrete_cls.__name__] = instance

        if declared_class is not None:
            self._instances[declared_class] = instance
            self._instances[declared_class.__name__] = instance

        return self

    def add_singleton(
        self,
        base_type: Any,
        concrete_type: Any = None,
    ) -> MicroContainer:
        """Register a singleton service resolved once and memoized.

        Args:
            base_type: Class, interface, or factory callable.
            concrete_type: Optional concrete class implementation.

        Returns:
            self for fluent chaining.
        """
        factory = concrete_type or base_type
        callable_factory = factory if callable(factory) else (lambda: factory)
        key = base_type
        self._factories[key] = (callable_factory, True)
        if hasattr(key, "__name__"):
            self._factories[key.__name__] = (callable_factory, True)
        if concrete_type is not None and hasattr(concrete_type, "__name__"):
            self._factories[concrete_type.__name__] = (callable_factory, True)
        return self

    def add_transient(
        self,
        base_type: Any,
        concrete_type: Any = None,
    ) -> MicroContainer:
        """Register a transient service freshly instantiated on every resolve.

        Args:
            base_type: Class, interface, or factory callable.
            concrete_type: Optional concrete class implementation.

        Returns:
            self for fluent chaining.
        """
        factory = concrete_type or base_type
        callable_factory = factory if callable(factory) else (lambda: factory)
        key = base_type
        self._factories[key] = (callable_factory, False)
        if hasattr(key, "__name__"):
            self._factories[key.__name__] = (callable_factory, False)
        if concrete_type is not None and hasattr(concrete_type, "__name__"):
            self._factories[concrete_type.__name__] = (callable_factory, False)
        return self

    def add_scoped(
        self,
        base_type: Any,
        concrete_type: Any = None,
    ) -> MicroContainer:
        """Register a scoped service (treated as singleton in single-threaded edge profiles).

        Args:
            base_type: Class, interface, or factory callable.
            concrete_type: Optional concrete class implementation.

        Returns:
            self for fluent chaining.
        """
        return self.add_singleton(base_type, concrete_type)

    def register(self, obj_type: type | str, *args: Any, **kwargs: Any) -> None:
        """Register a type conforming to ContainerProtocol.

        Args:
            obj_type: Type or name to register.
            args: Positional factory arguments.
            kwargs: Keyword factory arguments.
        """
        if args and callable(args[0]):
            self.add_transient(obj_type, args[0])
        else:
            self.add_transient(obj_type)

    @overload
    def resolve[R](self, obj_type: type[R], *args: Any, **kwargs: Any) -> R: ...

    @overload
    def resolve(self, obj_type: str, *args: Any, **kwargs: Any) -> Any: ...

    def resolve(self, obj_type: Any, *args: Any, **kwargs: Any) -> Any:
        """Resolve and return an instance of the requested service type or key.

        Args:
            obj_type: Class, interface, or string name to resolve.
            args: Optional positional arguments for instantiation.
            kwargs: Optional keyword arguments for instantiation.

        Returns:
            Activated service instance.

        Raises:
            CannotResolveException: If the service cannot be resolved.
        """
        # 1. Existing instance
        if obj_type in self._instances:
            return self._instances[obj_type]

        # 2. Registered factory
        if obj_type in self._factories:
            factory, is_singleton = self._factories[obj_type]
            instance = self._invoke_factory(factory, *args, **kwargs)
            if is_singleton:
                self.add_instance(
                    instance,
                    declared_class=obj_type if isinstance(obj_type, type) else None,
                )
            return instance

        # 3. Reflection on instantiable class
        if isinstance(obj_type, type) and not inspect.isabstract(obj_type):
            return self._instantiate_class(obj_type)

        raise CannotResolveException(obj_type)

    def _invoke_factory(
        self, factory: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        try:
            sig = inspect.signature(factory)
            if len(sig.parameters) == 0:
                return factory()
            if len(sig.parameters) == 1 and not args:
                return factory(self, **kwargs)
        except (ValueError, TypeError):
            pass
        return factory(*args, **kwargs)

    def _instantiate_class(self, cls: type[Any]) -> Any:
        try:
            sig = inspect.signature(cls.__init__)
        except (ValueError, TypeError):
            return cls()

        resolved_kwargs: dict[str, Any] = {}
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            if param.default is not inspect.Parameter.empty:
                continue
            if (
                param.annotation is not inspect.Parameter.empty
                and param.annotation in self
            ):
                resolved_kwargs[name] = self.resolve(param.annotation)

        return cls(**resolved_kwargs)

    def get[R](self, target_type: type[R]) -> R:
        """Retrieve a service instance by type conforming to service provider interfaces.

        Args:
            target_type: Requested type.

        Returns:
            Resolved instance.
        """
        return self.resolve(target_type)

    def build_provider(self) -> MicroContainer:
        """Build and return service provider (returns self in zero-overhead profile).

        Returns:
            self.
        """
        return self

    def __contains__(self, item: Any, /) -> bool:
        """Check if a service or interface is registered.

        Args:
            item: Class type or string identifier.

        Returns:
            True if configured, False otherwise.
        """
        if item in self._instances or item in self._factories:
            return True
        return bool(hasattr(item, "__name__") and item.__name__ in self._instances)


def create_container() -> ContainerPort:
    """Create a dependency injection container appropriate for the current runtime profile.

    Notes/Architectural Intent:
        Automatically selects between `rodi.Container` (for standard server/cloud environments)
        and `MicroContainer` (when executing on WASM, Pyodide, MicroPython, or when
        `rodi` is not installed), delivering seamless execution portability with 0 configuration.

    Returns:
        Instance conforming to ContainerPort.
    """
    if is_edge() or is_wasm() or is_micropython():
        return MicroContainer()

    try:
        from rodi import Container

        return Container()
    except ImportError:
        return MicroContainer()


__all__ = [
    "CannotResolveException",
    "ContainerException",
    "create_container",
    "MicroContainer",
]
